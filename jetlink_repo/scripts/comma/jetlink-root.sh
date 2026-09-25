#!/usr/bin/env bash
#
# Copyright (c) 2026-, Zeph Leggett.
# This file is part of jetlink and is licensed under the MIT License.
#
# Everything jetlink does as root on the comma, in one place. The owner runs it
# through jetlink/comma/root.py, which is sudo -n and a timeout:
#
#   sudo scripts/comma/jetlink-root.sh gadget            # the gadget for a Jetson or a Mac
#   sudo scripts/comma/jetlink-root.sh gadget --ios      # the gadget for an iPhone
#   sudo scripts/comma/jetlink-root.sh net               # after a bind, iOS only: address, DHCP
#   sudo scripts/comma/jetlink-root.sh check             # what is there now
#   sudo scripts/comma/jetlink-root.sh teardown
#   sudo scripts/comma/jetlink-root.sh port hold|off     # the USB-C port held as the device, or let go
#   sudo scripts/comma/jetlink-root.sh port device|reset # ask the far end to host over USB PD, or reset PD
#   sudo scripts/comma/jetlink-root.sh port source       # ask the far end for the source role: the comma charges it
#   sudo scripts/comma/jetlink-root.sh udc apply|restore # the USB device controller kept a device, or stock
#   sudo scripts/comma/jetlink-root.sh udc start|stop    # its device side turned on, or off
#   sudo scripts/comma/jetlink-root.sh vm apply|restore  # the link's VM tuning, or the stock values
#   sudo scripts/comma/jetlink-root.sh draw off|on       # no current drawn from the port (iOS), or the charger's own
#
# For the comma four and the comma 3X only. Both are SDM845 on the same AGNOS
# kernel (4.9, dwc3 at a600000.dwc3), with configfs, FunctionFS and NCM built
# in and no modules to load.
# The 3X is assumed from the kernel it shares with the four; only the four has been on the bench.
#
# gadget: the USB gadget, chosen by the comma's Jetlink setting. The
# comma is the USB device and the host runs the model; docs/transport.md says
# why. For a Jetson or a Mac (USB), the FunctionFS vendor interface alone. For
# an iPhone (iOS, with --ios), a composite: the vendor interface first, so it
# stays interface 0, and a CDC-NCM network interface after it, since an iPhone
# app can only use the network: the phone gets 192.168.60.x by DHCP from the
# dnsmasq this script starts on the gadget's netdev, and dials the comma at
# 192.168.60.1:5599.
#
# It does not bind the UDC: a FunctionFS gadget cannot attach to a controller
# until its descriptors are written, and the owner, which opens ep0, writes
# them and binds. The NCM function rides on that bind, and its netdev exists
# only from the first bind on, so the network is set up by net, which the owner
# runs after each bind.
#
# On failure the reason is left in $STATUS_FILE as well as on stderr, so the
# openpilot side can say why the link is unavailable. net reports in
# $NET_STATUS_FILE; it never fails the gadget.
set -euo pipefail

GADGET=/sys/kernel/config/usb_gadget/jetlink
FFS_MOUNT=/dev/ffs-jetlink
FFS_NAME=jetlink
CONFIGFS=/sys/kernel/config
# who openpilot runs as: the owner opens the endpoints and binds the UDC as it
OPENPILOT_USER=comma
# tmpfs on purpose: per-boot state, and the comma's flash is precious
STATUS_FILE=/dev/shm/jetlink-gadget
NET_STATUS_FILE=/dev/shm/jetlink-net
# pid.codes test allocation; get a real PID before distributing this
VID=0x1209
PID=0x0001
NET_IF=usb0    # the function name suffix only; see net_ifname for the netdev
# NCM batches packets, which a 460 KB frame benefits from
NET_FN=ncm.$NET_IF
COMMA_ADDR=192.168.60.1
COMMA_PREFIX=24
# The whole subnet and short leases: the comma's 4.9 kernel gives the host a new
# random MAC every bind, so each bind is a new DHCP client. With 8 addresses and
# an hour's lease, eight rebinds in an hour left the next host without one.
DHCP_RANGE=192.168.60.2,192.168.60.254,10m
DNSMASQ_PID=/dev/shm/jetlink-dnsmasq.pid
DNSMASQ_IF=/dev/shm/jetlink-dnsmasq.if
DNSMASQ_LEASES=/dev/shm/jetlink-usb0.leases

# port: the charger's DISABLE_POWER_ROLE_SWITCH voter on the PMI8998, the one
# role lever that holds across plugs, and the policy engine's own USB PD
# requests; jetlink/comma/port.py says when each is used
POWER_ROLE_VOTER=${JETLINK_POWER_ROLE_VOTER:-/sys/kernel/debug/pmic-votable/DISABLE_POWER_ROLE_SWITCH}
USBPD=${JETLINK_USBPD:-/sys/class/usbpd/usbpd0}
DUAL_ROLE=${JETLINK_DUAL_ROLE:-/sys/class/dual_role_usb/otg_default}

# udc: the dwc3 glue for the port's controller (usb0, ssusb@a600000) and the
# policy engine's parameters. Both have a usb_compliance_mode, and each gates
# one place only: the policy engine's turns the device side on at every sink
# attach, not just when the charger detection read a USB port (SDP, CDP or
# floating lines); the glue's keeps dwc3 from turning it off again when the
# lines read floating and no host enumerated it in 10 s. An Apple port connects
# its data lines only after USB PD, and at boot no gadget is bound for 10 s.
UDC_GLUE=${JETLINK_UDC_GLUE:-/sys/devices/platform/soc/a600000.ssusb}
PE_PARAMS=${JETLINK_PE_PARAMS:-/sys/module/policy_engine/parameters}
USB_PSY=${JETLINK_USB_PSY:-/sys/class/power_supply/usb}

# draw: the charger's USB_ICL voter, the input current limit on the port. As
# the sink the charger draws up to 900 mA from whatever powers the port, though
# the comma runs on its own supply. An iPhone powers what it plugs into with
# little current; under that draw its supply sags, the charger's weak-charger
# and reverse-boost handlers cut and restore the input in a loop, and the phone
# never sees a device. Forced to 0 the input is suspended: the port still reads
# present and the roles still settle, and those handlers stand down at 25 mA or
# less. As the source the kernel votes the input to 0 itself.
USB_ICL_VOTER=${JETLINK_USB_ICL_VOTER:-/sys/kernel/debug/pmic-votable/USB_ICL}

# vm: loggerd's dirty pages pile up until the kernel reclaims them
# synchronously, right while a FunctionFS transfer allocates its buffer: gadget
# reads stalled 200-350 ms and the big model fell back. Capping dirty memory
# keeps that reclaim cheap. System-wide, since the gadget read shares the
# kernel with every writer.
# Not vm.min_free_kbytes: a 128 MB floor takes about three times that out of
# MemAvailable, 360 MB on a 3.6 GB comma, and openpilot's LOW MEMORY alert
# reads MemTotal-MemAvailable against 90 %. Drives at 80 % showed 90 and
# alerted. The caps alone are not yet re-measured against the stall.
# And the socket buffer caps, for the iPhone's TCP link: transport/tcp.py asks
# for 4 MB, which turns autotuning off, and the kernel clamps it to these, 224
# KB on AGNOS and so 448 KB of buffer. A 393 KB frame in 1448-byte segments does
# not fit, so the send waited on the phone's ACKs: 6 to 50 ms, following its
# round trip. With 4 MB the frame goes in one write and the send took ~4 ms
# (a tester's comma, 2026-10-04). Only a socket that asks gets more; one set up
# before the apply keeps the old cap until the phone reconnects.
VM_SYSCTLS=(vm.dirty_bytes=16777216 vm.dirty_background_bytes=8388608
            net.core.wmem_max=4194304 net.core.rmem_max=4194304)
PROC_SYS=${JETLINK_PROC_SYS:-/proc/sys}
# the stock values to write back, one key=value a line, recorded by the first
# apply and dropped by restore
SYSCTL_PREV=${JETLINK_SYSCTL_PREV:-/dev/shm/jetlink-sysctl-prev}

usage() {
  echo "usage: $0 gadget [--ios] | net | check | teardown | port hold|off|device|reset|source|sink | udc apply|restore|start|stop | vm apply|restore | draw off|on" >&2
  exit 2
}

status() {
  # best effort: a device with no /dev/shm still gets the stderr line
  { echo "$1" > "$STATUS_FILE" && chmod 0644 "$STATUS_FILE"; } 2>/dev/null || true
}

net_status() {
  { echo "$1" > "$NET_STATUS_FILE" && chmod 0644 "$NET_STATUS_FILE"; } 2>/dev/null || true
}

fail() {
  echo "jetlink: $1" >&2
  status "error: $1"
  exit 1
}

# -- the gadget's network, iOS only -------------------------------------------

net_present() {
  [[ -d "$GADGET/functions/$NET_FN" ]]
}

dnsmasq_alive() {
  local pid
  pid=$(cat "$DNSMASQ_PID" 2>/dev/null || true)
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# The interface the kernel gave the network function. The function is named
# ncm.usb0 but the netdev is not usb0: the modem already holds that name on a
# comma, so ours comes up as usb1 or later, and the number can change from one
# bind to the next. u_ether records the real name in the function's ifname,
# readable only while the gadget is bound.
net_ifname() {
  local name
  name=$(cat "$GADGET/functions/$NET_FN/ifname" 2>/dev/null || true)
  [[ -n "$name" && -d "/sys/class/net/$name" ]] || return 1
  echo "$name"
}

# The comma's end of the cable network. Idempotent, and never fatal. The owner
# runs it through net once it has bound the UDC and the interface has appeared.
net_up() {
  local dev why
  if ! dev=$(net_ifname); then
    net_status "error: no netdev yet; it appears when the owner binds the UDC (then run net)"
    echo "$NET_FN present, its netdev not yet created (appears at bind); run net after binding" >&2
    return 0
  fi
  # NetworkManager manages every device on AGNOS and would DHCP on it itself
  nmcli dev set "$dev" managed no >/dev/null 2>&1 || true
  if ! ip addr replace "$COMMA_ADDR/$COMMA_PREFIX" dev "$dev" 2>/dev/null; then
    why="could not set $COMMA_ADDR/$COMMA_PREFIX on $dev"
    net_status "error: $why"; echo "jetlink: $why" >&2
    return 0
  fi
  if ! ip link set "$dev" up 2>/dev/null; then
    why="could not bring $dev up"
    net_status "error: $why"; echo "jetlink: $why" >&2
    return 0
  fi
  # Steer receive processing onto the big cores: the comma's little cores add
  # milliseconds to a 460 KB frame.
  if [[ -w "/sys/class/net/$dev/queues/rx-0/rps_cpus" ]]; then
    echo f0 > "/sys/class/net/$dev/queues/rx-0/rps_cpus" 2>/dev/null || true
  fi
  # DHCP for the phone, and only that: no router (option 3) and no DNS (option 6),
  # so the phone keeps its default route over Wi-Fi. No DNS service (--port=0).
  # dnsmasq binds the interface by name, so a netdev that came back under a new
  # name after a rebind needs a fresh dnsmasq: the running one is on a ghost.
  if dnsmasq_alive && [[ "$(cat "$DNSMASQ_IF" 2>/dev/null || true)" != "$dev" ]]; then
    kill "$(cat "$DNSMASQ_PID")" 2>/dev/null || true
    sleep 0.2
  fi
  if ! dnsmasq_alive; then
    rm -f "$DNSMASQ_PID" 2>/dev/null || true
    if ! dnsmasq --conf-file=/dev/null --bind-interfaces --interface="$dev" \
        --except-interface=lo --port=0 --dhcp-range="$DHCP_RANGE" \
        --dhcp-option=3 --dhcp-option=6 --dhcp-leasefile="$DNSMASQ_LEASES" \
        --pid-file="$DNSMASQ_PID" 2>/dev/null; then
      why="dnsmasq would not start on $dev"
      net_status "error: $why"; echo "jetlink: $why" >&2
      return 0
    fi
    echo "$dev" > "$DNSMASQ_IF"
  fi
  net_status "ok $COMMA_ADDR $dev"
  echo "$dev (ncm) at $COMMA_ADDR/$COMMA_PREFIX, DHCP $DHCP_RANGE"
  return 0
}

net_down() {
  local pid
  pid=$(cat "$DNSMASQ_PID" 2>/dev/null || true)
  if [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$DNSMASQ_PID" 2>/dev/null || true
}

# The network function and its DHCP server, gone: for teardown, and for a USB
# gadget left with one by an iOS boot. Unlinking it force-unbinds the UDC.
net_remove() {
  local f
  net_down
  for f in "$GADGET"/configs/c.1/*."$NET_IF"; do
    if [[ -L "$f" ]]; then rm -f "$f" 2>/dev/null || true; fi
  done
  for f in "$GADGET"/functions/*."$NET_IF"; do
    if [[ -d "$f" ]]; then rmdir "$f" 2>/dev/null || true; fi
  done
}

# -- subcommands ----------------------------------------------------------------

cmd_gadget() {
  local ios=0 udcs other owner bound serial uid gid
  case "${1:-}" in
    "") ;;
    --ios) ios=1 ;;
    *) usage ;;
  esac
  [[ $EUID -eq 0 ]] || fail "jetlink-root.sh gadget must run as root"

  # set -e alone exits without going through fail, leaving last boot's "ok" in
  # $STATUS_FILE for the openpilot side to read.
  trap 'fail "line $LINENO: $BASH_COMMAND failed"' ERR

  mountpoint -q "$CONFIGFS" || mount -t configfs none "$CONFIGFS" 2>/dev/null || true
  mountpoint -q "$CONFIGFS" || fail "no configfs at $CONFIGFS; this kernel cannot configure a USB gadget"

  # absent means this AGNOS build has no CONFIG_USB_LIBCOMPOSITE, which nothing
  # in userspace can fix
  [[ -d "$CONFIGFS/usb_gadget" ]] || fail "kernel has no USB gadget support (CONFIG_USB_LIBCOMPOSITE); jetlink needs an AGNOS build that has it"

  # No FunctionFS preflight on purpose: the kernel registers the functionfs
  # filesystem only while some ffs.* function exists, so /proc/filesystems never
  # lists it on a cold boot. The mkdir, mount and ep0 checks below test it in use.

  # a gadget needs a device controller
  shopt -s nullglob
  udcs=("/sys/class/udc"/*)
  shopt -u nullglob
  [[ ${#udcs[@]} -gt 0 ]] || fail "no USB device controller in /sys/class/udc; this device cannot act as a USB gadget"

  # refuse to fight another gadget for the controller rather than unbinding it
  for other in "$CONFIGFS"/usb_gadget/*/UDC; do
    if [[ -e "$other" ]]; then
      owner=$(basename "$(dirname "$other")")
      bound=$(cat "$other" 2>/dev/null || true)
      if [[ "$owner" != "jetlink" && -n "$bound" ]]; then
        fail "USB gadget '$owner' already holds the device controller ($bound); tear it down first"
      fi
    fi
  done

  mkdir -p "$GADGET" || fail "could not create the gadget at $GADGET"
  cd "$GADGET"

  echo "$VID"   > idVendor
  echo "$PID"   > idProduct
  echo 0x0320   > bcdUSB            # 3.2: advertise SuperSpeed
  if [[ $ios -eq 1 ]]; then
    # its own bcdDevice, so hosts that cache descriptors by VID/PID/bcdDevice
    # (macOS, Windows) fetch the composite ones rather than the plain gadget's
    echo 0x0101 > bcdDevice
    # Miscellaneous / Common Class / IAD: the composite device class, which tells
    # a host to bind a driver per interface association (the vendor interface
    # for jetlink, CDC-NCM for the network) rather than one for the whole device
    echo 0xEF   > bDeviceClass
    echo 0x02   > bDeviceSubClass
    echo 0x01   > bDeviceProtocol
  else
    # the plain gadget, as it has always been: class per interface
    echo 0x0100 > bcdDevice
    echo 0x00   > bDeviceClass
    echo 0x00   > bDeviceSubClass
    echo 0x00   > bDeviceProtocol
  fi

  # The device tree carries a serial on some commas and not others; any stable
  # string will do.
  serial=$({ tr -d '\0' < /proc/device-tree/serial-number; } 2>/dev/null || cat /etc/machine-id 2>/dev/null || echo 0001)
  [[ -n "$serial" ]] || serial=0001
  mkdir -p strings/0x409
  echo "zoompilot"  > strings/0x409/manufacturer
  echo "jetlink"    > strings/0x409/product
  echo "$serial"    > strings/0x409/serialnumber

  mkdir -p configs/c.1/strings/0x409
  echo "jetlink inference link" > configs/c.1/strings/0x409/configuration
  # self-powered, and as little as the spec allows: the Jetson has its own 12 V feed
  echo 0xC0 > configs/c.1/bmAttributes
  echo 8    > configs/c.1/MaxPower

  # the mkdir instantiates the function and registers functionfs, so a kernel
  # genuinely without it fails here
  mkdir -p "functions/ffs.$FFS_NAME" ||
    fail "kernel has no ffs gadget function (CONFIG_USB_CONFIGFS_F_FS); jetlink cannot present its endpoints"
  # Link once: this is re-run on every deploy, and unlinking a function from a bound
  # config force-unbinds the UDC, so an unconditional ln -sf drops a live link.
  # Linked before the network function so it is interface 0: hosts that open the
  # vendor interface by number depend on that.
  [[ -L "configs/c.1/ffs.$FFS_NAME" ]] ||
    ln -s "$GADGET/functions/ffs.$FFS_NAME" "configs/c.1/ffs.$FFS_NAME" ||
    fail "could not link ffs.$FFS_NAME into configs/c.1"

  # The network interface, for an iPhone only. A USB gadget left with one from an
  # iOS boot loses it here: unlinking it force-unbinds the UDC, which is why the
  # owner switches only while parked. The 4.9 kernel picks the interface's MAC
  # addresses itself and refuses them from configfs; DHCP makes that harmless.
  if [[ $ios -eq 0 ]]; then
    if net_present; then net_remove; fi
  else
    mkdir -p "functions/$NET_FN" || fail "could not create the $NET_FN gadget function"
    # after ffs, so it takes the next interface numbers
    [[ -L "configs/c.1/$NET_FN" ]] ||
      ln -s "$GADGET/functions/$NET_FN" "configs/c.1/$NET_FN" ||
      fail "could not link $NET_FN into configs/c.1"
  fi

  mkdir -p "$FFS_MOUNT"
  # Owned by the user openpilot runs as: on a root-only mount the owner and
  # modeld cannot open the endpoints, and Path.exists() raises rather than
  # returning False.
  uid=$(id -u "$OPENPILOT_USER")
  gid=$(id -g "$OPENPILOT_USER")
  mountpoint -q "$FFS_MOUNT" || mount -t functionfs -o "uid=$uid,gid=$gid" "$FFS_NAME" "$FFS_MOUNT" ||
    fail "could not mount functionfs at $FFS_MOUNT"

  # the check that proves the chain: ep0 is what the owner opens to write the
  # descriptors and bind the controller
  [[ -e "$FFS_MOUNT/ep0" ]] || fail "functionfs mounted at $FFS_MOUNT but has no ep0"

  # the owner binds the UDC as the openpilot user, so hand it that one attribute
  chown "$OPENPILOT_USER" "$GADGET/UDC" 2>/dev/null || true

  status ok
  echo "gadget ready at $GADGET"
  echo "functionfs mounted at $FFS_MOUNT"
  if [[ $ios -eq 1 ]]; then
    echo "network function: $NET_FN (after ffs.$FFS_NAME in configs/c.1)"
    # its netdev appears at the owner's bind, and net sets it up then
    rm -f "$NET_STATUS_FILE" 2>/dev/null || true
  else
    net_status "net: off"
  fi
  echo "available UDCs: ${udcs[*]##*/}"
  echo "the owner writes the descriptors and binds the UDC"
}

cmd_net() {
  [[ $EUID -eq 0 ]] || fail "jetlink-root.sh net must run as root"
  [[ -d "$GADGET" ]] || { net_status "error: no gadget"; fail "no gadget at $GADGET; run gadget first"; }
  net_up
}

cmd_teardown() {
  local f linked=0
  net_remove
  if [[ -d "$GADGET" ]]; then
    echo "" > "$GADGET/UDC" 2>/dev/null || true
    rm -f "$GADGET/configs/c.1/ffs.$FFS_NAME" 2>/dev/null || true
    rmdir "$GADGET/configs/c.1/strings/0x409" 2>/dev/null || true
    # a config with a function still linked cannot go, and trying is a
    # configfs error worth not making
    for f in "$GADGET"/configs/c.1/*; do
      if [[ -L "$f" ]]; then linked=1; fi
    done
    if [[ $linked -eq 0 ]]; then
      rmdir "$GADGET/configs/c.1" 2>/dev/null || true
    else
      echo "jetlink: configs/c.1 still has a function linked; left in place" >&2
    fi
    rmdir "$GADGET/functions/ffs.$FFS_NAME" 2>/dev/null || true
    rmdir "$GADGET/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET" 2>/dev/null || true
  fi
  # A plain umount can block or segfault on a FunctionFS instance whose owner died
  # with endpoints open; lazy-detach unhooks it now and lets the kernel finish.
  umount -l "$FFS_MOUNT" 2>/dev/null || umount "$FFS_MOUNT" 2>/dev/null || true
  rmdir "$FFS_MOUNT" 2>/dev/null || true
  status "error: gadget torn down"
  net_status "error: gadget torn down"
  echo "jetlink gadget torn down"
}

cmd_check() {
  local u g dev udcs
  [[ $EUID -eq 0 ]] || { echo "run check as root (sudo)" >&2; exit 1; }
  echo "kernel: $(uname -r)"
  if mountpoint -q "$CONFIGFS" && [[ -d "$CONFIGFS/usb_gadget" ]]; then
    echo "configfs USB gadgets: yes"
  else
    echo "configfs USB gadgets: NO (no $CONFIGFS/usb_gadget)"
  fi
  shopt -s nullglob
  udcs=(/sys/class/udc/*)
  shopt -u nullglob
  for u in "${udcs[@]}"; do
    # current_speed is the negotiated bus speed: super-speed is USB 3, and a
    # 460 KB frame is ~1 ms there against ~11 ms at high-speed (USB 2). The
    # owner logs it on every configured edge, since nothing in this script
    # runs after enumeration.
    echo "device controller: $(basename "$u"), state $(cat "$u/state" 2>/dev/null || echo unknown), speed $(cat "$u/current_speed" 2>/dev/null || echo unknown)"
  done
  [[ ${#udcs[@]} -gt 0 ]] || echo "device controller: NONE"
  for g in "$CONFIGFS"/usb_gadget/*/; do
    [[ -d "$g" ]] || continue
    echo "gadget $(basename "$g"): bound to '$(cat "$g/UDC" 2>/dev/null)'"
  done
  echo "gadget status: $(cat "$STATUS_FILE" 2>/dev/null || echo none)"
  # A phone plugged straight into the comma negotiates power and the comma may
  # end up sourcing it, which reboots the comma. Through a hub the comma sinks.
  # On a C-to-C cable the comma can come out the host instead; port hold fixes that.
  if [[ -d "$USBPD" ]]; then
    echo "USB-C port: power role $(cat "$USBPD/current_pr" 2>/dev/null || echo unknown), data role $(cat "$USBPD/current_dr" 2>/dev/null || echo unknown), USB PD contract $(cat "$USBPD/contract" 2>/dev/null || echo unknown), Type-C $(cat "$USB_PSY/typec_mode" 2>/dev/null || echo unknown)"
  fi
  if [[ "$(cat "$POWER_ROLE_VOTER/force_active" 2>/dev/null || true)" == 1 ]]; then
    echo "USB-C port: held as the device (port hold)"
  fi
  if [[ "$(cat "$USB_ICL_VOTER/force_active" 2>/dev/null || true)" == 1 ]]; then
    echo "USB-C port: no current drawn from it (draw off)"
  fi
  if [[ -d "$UDC_GLUE" ]]; then
    echo "USB device controller: $(cat "$UDC_GLUE/mode" 2>/dev/null || echo unknown), charger detection $(cat "$USB_PSY/real_type" 2>/dev/null || echo unknown), kept a device $(cat "$PE_PARAMS/usb_compliance_mode" 2>/dev/null || echo '?')/$(cat "$UDC_GLUE/usb_compliance_mode" 2>/dev/null || echo '?')"
  fi
  if ! net_present; then
    echo "network function: none (the USB gadget, or no gadget)"
    return 0
  fi
  echo "network function: $NET_FN"
  if dev=$(net_ifname); then
    echo "$dev: $(cat "/sys/class/net/$dev/operstate" 2>/dev/null || echo unknown), $(ip -4 -o addr show dev "$dev" 2>/dev/null | awk '{print $4}' | tr '\n' ' ')"
  else
    echo "netdev: absent (it appears when the owner binds the UDC)"
  fi
  echo "network status: $(cat "$NET_STATUS_FILE" 2>/dev/null || echo unknown)"
  if dnsmasq_alive; then echo "dnsmasq: running"; else echo "dnsmasq: not running"; fi
}

# The comma's USB-C port, for a link that runs over USB. hold keeps the port at
# sink, which makes the far end the host; off is dual role, as AGNOS boots it.
# device asks the far end over USB PD to take the host role (a DR_Swap): for a
# far end that powers the comma and still came out the device, which hold
# cannot change. reset is a USB PD hard reset, which puts both ends back to
# the roles their power gives them: a sink is the device. source asks a far end
# that powers the comma for the source role (a PR_Swap), which leaves the data
# roles as they are: an iPhone that hosts the comma stays the host and charges
# from it. The voter gates it, so port off comes first. sink is the swap back,
# for a phone whose link went down once it charged.
cmd_port() {
  case "${1:-}" in
    hold) force_voter "$POWER_ROLE_VOTER" 1 "to hold the port" || exit 1 ;;
    # letting go applies the voters' own result, which is dual role
    off) release_voter "$POWER_ROLE_VOTER" || exit 1 ;;
    # the kernel sends the DR_Swap and waits 100 ms for it; a refusal, or PD not
    # ready yet, is a failed write
    device) put device "$DUAL_ROLE/data_role" "the far end did not take the host role ($DUAL_ROLE/data_role)" || exit 1 ;;
    reset) put 1 "$USBPD/hard_reset" "could not reset USB PD ($USBPD/hard_reset)" || exit 1 ;;
    # the kernel sends the PR_Swap and waits up to 2 s for it; only with a USB PD
    # contract, so a write before one, or a refusal, fails
    source) put source "$DUAL_ROLE/power_role" "the far end did not give up the source role ($DUAL_ROLE/power_role)" || exit 1 ;;
    sink) put sink "$DUAL_ROLE/power_role" "the far end did not take the source role back ($DUAL_ROLE/power_role)" || exit 1 ;;
    *) usage ;;
  esac
}

# The port's USB device controller, while the link is on. apply keeps it a
# device whatever the charger detection made of the far end's data lines, and
# restore puts the stock behaviour back; see UDC_GLUE. start turns the device
# side on now, for a host that powers the port while it is off, and stop turns
# it off again once that host is gone.
cmd_udc() {
  case "${1:-}" in
    apply) udc_compliance Y || exit 1 ;;
    restore) udc_compliance N || exit 1 ;;
    start) put peripheral "$UDC_GLUE/mode" "could not start the USB device controller ($UDC_GLUE/mode)" || exit 1 ;;
    stop) put none "$UDC_GLUE/mode" "could not stop the USB device controller ($UDC_GLUE/mode)" || exit 1 ;;
    *) usage ;;
  esac
}

# Both knobs, each on its own, so one the kernel lacks does not keep the other.
udc_compliance() {
  local failed=0 knob
  for knob in "$PE_PARAMS/usb_compliance_mode" "$UDC_GLUE/usb_compliance_mode"; do
    put "$1" "$knob" "could not set $knob" || failed=1
  done
  return $failed
}

# One value into one kernel file; a line on stderr, with the kernel's reason,
# and a failure when the kernel refuses it. Not fail(): that is the gadget's record.
put() {
  local err
  if ! err=$( { echo "$1" > "$2"; } 2>&1 ); then
    echo "jetlink: $3${err:+: ${err##*: }}" >&2
    return 1
  fi
}

# A charger voter under debugfs forced to a value, and let go: force_val first,
# since forcing applies whatever force_val holds at that moment.
force_voter() {
  { echo "$2" > "$1/force_val" && echo 1 > "$1/force_active"; } 2>/dev/null ||
    { echo "jetlink: could not force $1 $3" >&2; return 1; }
}

release_voter() {
  { echo 0 > "$1/force_active" && echo 0 > "$1/force_val"; } 2>/dev/null ||
    { echo "jetlink: could not release $1" >&2; return 1; }
}

# One key per write, so a value the kernel rejects does not take the rest with it.
sysctl_write() {
  put "$2" "$PROC_SYS/${1//.//}" "could not set $1=$2"
}

# Applied while the link is on, so a device with the link off runs stock
# values. Only restore undoes them, never an exit: a process that restored on
# exit and stopped at ignition would hand every drive the stock values. A
# reboot resets them.
vm_apply() {
  local pair key value rec="" failed=0
  if [[ ! -e "$SYSCTL_PREV" ]]; then
    for pair in "${VM_SYSCTLS[@]}"; do
      key=${pair%%=*}
      value=""
      { read -r value < "$PROC_SYS/${key//.//}"; } 2>/dev/null || true
      if [[ "$value" == 0 && "$key" == *_bytes ]]; then
        # Stock AGNOS runs the dirty limits in ratio mode, so the *_bytes keys
        # read 0, and the kernel silently drops a 0 written back to one.
        # Writing the ratio key is what zeroes the bytes key, so that is the
        # one to put back.
        key=${key%_bytes}_ratio
        value=""
        { read -r value < "$PROC_SYS/${key//.//}"; } 2>/dev/null || true
      fi
      if [[ -n "$value" ]]; then
        rec+="$key=$value"$'\n'
      else
        echo "jetlink: could not read $key" >&2
      fi
    done
    if [[ -n "$rec" ]]; then
      { printf '%s' "$rec" > "$SYSCTL_PREV" && chmod 0644 "$SYSCTL_PREV"; } 2>/dev/null ||
        echo "jetlink: could not record the previous sysctls in $SYSCTL_PREV" >&2
    fi
  fi
  for pair in "${VM_SYSCTLS[@]}"; do
    sysctl_write "${pair%%=*}" "${pair#*=}" || failed=1
  done
  return $failed
}

# Writes the record back line by line: a vm or net.core key and a number,
# nothing else.
vm_restore() {
  local key value failed=0
  [[ -e "$SYSCTL_PREV" ]] || return 0
  while IFS='=' read -r key value; do
    if [[ "$key" =~ ^(vm|net\.core)\.[a-z_]+$ && "$value" =~ ^[0-9]+$ ]]; then
      sysctl_write "$key" "$value" || failed=1
    else
      echo "jetlink: not restoring '$key=$value' from $SYSCTL_PREV" >&2
      failed=1
    fi
  done < "$SYSCTL_PREV"
  rm -f "$SYSCTL_PREV" 2>/dev/null || true
  return $failed
}

cmd_vm() {
  case "${1:-}" in
    apply) vm_apply || exit 1 ;;
    restore) vm_restore || exit 1 ;;
    *) usage ;;
  esac
}

# The port's input current while the link is iOS; see USB_ICL_VOTER. off forces
# the limit to 0 and on gives the charger its own limit back. Like udc and vm,
# undone only by on, never at an exit; a reboot clears it.
cmd_draw() {
  case "${1:-}" in
    off) force_voter "$USB_ICL_VOTER" 0 "to stop drawing from the port" || exit 1 ;;
    on) release_voter "$USB_ICL_VOTER" || exit 1 ;;
    *) usage ;;
  esac
}

cmd=${1:-}
if [[ $# -gt 0 ]]; then shift; fi
case "$cmd" in
  gadget) cmd_gadget "$@" ;;
  net) cmd_net ;;
  check) cmd_check ;;
  teardown) cmd_teardown ;;
  port) cmd_port "$@" ;;
  udc) cmd_udc "$@" ;;
  vm) cmd_vm "$@" ;;
  draw) cmd_draw "$@" ;;
  *) usage ;;
esac
