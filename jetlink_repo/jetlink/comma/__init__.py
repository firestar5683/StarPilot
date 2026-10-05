"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

What runs on the comma itself, beside openpilot: the USB gadget (gadget), the
process that holds it for the whole time the link is on (owner), the lease
other processes borrow its endpoints on (lending), the USB-C port (port), and
the one root script all of it goes through (root), the VM tuning included. For
the comma four and the comma 3X.

The standard library and jetlink's transport only: the owner that imports it
stays resident at about 10 MB. openpilot starts the owner through
jetlink.openpilot.owner, with what the fork's adapter names: the settings, the
chestnut's USB ids and the provisioning worker.
"""
