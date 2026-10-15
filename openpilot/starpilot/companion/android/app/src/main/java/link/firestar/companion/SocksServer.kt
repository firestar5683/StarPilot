package link.firestar.companion

import java.io.Closeable
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.*
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.Semaphore
import java.util.concurrent.atomic.AtomicBoolean

interface CellularTransport {
    fun resolve(host: String): Array<InetAddress>
    fun socket(): Socket
    fun datagram(): DatagramSocket
}

/** RFC 1928 CONNECT + UDP ASSOCIATE and RFC 1929 authentication. No DNS on Wi-Fi. */
class SocksServer(private val wifi: Inet4Address, private val cellular: CellularTransport,
                  private val user: String, private val password: String, private val count: (Int) -> Unit, private val gateway: String = "172.31.254.1", listenPort: Int = 1080) : Closeable {
    private val open = AtomicBoolean(true)
    private val resources = ConcurrentHashMap.newKeySet<Closeable>()
    private val clients = Semaphore(24)
    private val pool = Executors.newCachedThreadPool()
    private val server = ServerSocket().apply { reuseAddress = true; bind(InetSocketAddress(wifi, listenPort), 24) }
    val port: Int get() = server.localPort
    @Volatile var deniedHosts: Set<String> = setOf("commadataci.blob.core.windows.net", "commadata2.blob.core.windows.net", "upload.comma.ai", "logs.comma.ai")
    init {
        resources.add(server)
        pool.execute {
            while (open.get()) {
                val socket = try { server.accept() } catch (_: Exception) { break }
                // Only the comma gateway may use this listener, even with credentials.
                if (socket.inetAddress.hostAddress != gateway || !clients.tryAcquire()) { socket.close(); continue }
                resources.add(socket)
                pool.execute { try { serve(socket) } catch (_: Exception) { } finally { resources.remove(socket); socket.close(); clients.release() } }
            }
        }
    }
    private fun DataInputStream.string(): String {
        val length = readUnsignedByte()
        require(length > 0)
        return ByteArray(length).also { readFully(it) }.toString(Charsets.UTF_8)
    }
    private data class Target(val host: String, val port: Int)
    private fun target(input: DataInputStream): Target {
        val host = when (input.readUnsignedByte()) {
            1 -> InetAddress.getByAddress(ByteArray(4).also { input.readFully(it) }).hostAddress!!
            3 -> input.string()
            4 -> InetAddress.getByAddress(ByteArray(16).also { input.readFully(it) }).hostAddress!!
            else -> throw IllegalArgumentException("Unsupported address type")
        }
        return Target(host, input.readUnsignedShort())
    }
    private fun resolve(target: Target): InetAddress {
        val host = target.host.lowercase().trimEnd('.')
        require(target.port in 1..65535 && host.length <= 253)
        require(deniedHosts.none { host == it || host.endsWith(".$it") })
        return cellular.resolve(host).firstOrNull {
            !it.isAnyLocalAddress && !it.isLoopbackAddress && !it.isLinkLocalAddress && !it.isSiteLocalAddress && !it.isMulticastAddress &&
                !(it.address.size == 16 && (it.address[0].toInt() and 0xfe) == 0xfc)
        } ?: throw IllegalArgumentException("No public cellular address")
    }
    private fun reply(output: DataOutputStream, code: Int, address: InetAddress = wifi, port: Int = 0) {
        output.write(byteArrayOf(5, code.toByte(), 0, if (address.address.size == 4) 1 else 4))
        output.write(address.address); output.writeShort(port); output.flush()
    }
    private fun serve(client: Socket) {
        client.soTimeout = 10000
        val input = DataInputStream(client.getInputStream())
        val output = DataOutputStream(client.getOutputStream())
        require(input.readUnsignedByte() == 5)
        val methods = ByteArray(input.readUnsignedByte()).also { input.readFully(it) }
        output.write(byteArrayOf(5, if (methods.contains(2)) 2 else 0xff.toByte())); output.flush()
        if (!methods.contains(2)) return
        require(input.readUnsignedByte() == 1)
        val valid = input.string() == user && input.string() == password
        output.write(byteArrayOf(1, if (valid) 0 else 1)); output.flush()
        if (!valid) return
        require(input.readUnsignedByte() == 5)
        val command = input.readUnsignedByte()
        require(input.readUnsignedByte() == 0)
        val destination = target(input)
        when (command) {
            1 -> {
                val remote = cellular.socket()
                resources.add(remote)
                try {
                    try { remote.connect(InetSocketAddress(resolve(destination), destination.port), 8000) }
                    catch (_: Exception) { reply(output, 4); return }
                    reply(output, 0)
                    client.soTimeout = 120000; remote.soTimeout = 120000
                    val upstream = pool.submit { pump(client, remote) }
                    pump(remote, client)
                    upstream.get(125, java.util.concurrent.TimeUnit.SECONDS)
                } finally { resources.remove(remote); remote.close() }
            }
            3 -> udp(client, input, output)
            else -> reply(output, 7)
        }
    }
    private fun pump(source: Socket, destination: Socket) {
        try {
            val buffer = ByteArray(32768)
            val input = source.getInputStream(); val output = destination.getOutputStream()
            while (open.get()) {
                val size = input.read(buffer)
                if (size < 0) break
                count(size); output.write(buffer, 0, size)
            }
            destination.shutdownOutput()
        } catch (_: Exception) { try { source.close(); destination.close() } catch (_: Exception) { } }
    }
    private fun udp(client: Socket, input: DataInputStream, output: DataOutputStream) {
        val local = DatagramSocket(InetSocketAddress(wifi, 0))
        resources.add(local)
        try {
            val outbound = cellular.datagram()
            resources.add(outbound)
            try { relayUdp(client, input, output, local, outbound) }
            finally { outbound.close(); resources.remove(outbound) }
        } finally { local.close(); resources.remove(local) }
    }
    private fun relayUdp(client: Socket, input: DataInputStream, output: DataOutputStream,
                         local: DatagramSocket, outbound: DatagramSocket) {
        val association = AtomicBoolean(true)
        val allowed = ConcurrentHashMap.newKeySet<InetSocketAddress>()
        var peer: InetSocketAddress? = null
        val peerLock = Any()
        reply(output, 0, wifi, local.localPort)
        val sender = pool.submit {
            val buffer = ByteArray(65535)
            while (association.get() && open.get()) {
                try {
                    val packet = DatagramPacket(buffer, buffer.size); local.receive(packet)
                    if (packet.address != client.inetAddress) continue
                    val senderAddress = InetSocketAddress(packet.address, packet.port)
                    synchronized(peerLock) { if (peer == null) peer = senderAddress }
                    if (synchronized(peerLock) { peer } != senderAddress) continue
                    val bytes = DataInputStream(packet.data.inputStream(0, packet.length))
                    if (bytes.readUnsignedShort() != 0 || bytes.readUnsignedByte() != 0) continue // No fragments.
                    val destination = target(bytes)
                    val remote = InetSocketAddress(resolve(destination), destination.port)
                    if (allowed.size >= 128 && !allowed.contains(remote)) continue
                    allowed.add(remote)
                    val payload = bytes.readBytes()
                    outbound.send(DatagramPacket(payload, payload.size, remote)); count(payload.size)
                } catch (_: Exception) { if (local.isClosed || outbound.isClosed) break }
            }
        }
        val receiver = pool.submit {
            val buffer = ByteArray(65535)
            while (association.get() && open.get()) {
                try {
                    val packet = DatagramPacket(buffer, buffer.size); outbound.receive(packet)
                    if (!allowed.contains(InetSocketAddress(packet.address, packet.port))) continue
                    val receiverAddress = synchronized(peerLock) { peer } ?: continue
                    val framed = java.io.ByteArrayOutputStream()
                    val header = DataOutputStream(framed)
                    header.writeShort(0); header.writeByte(0); header.writeByte(if (packet.address.address.size == 4) 1 else 4)
                    header.write(packet.address.address); header.writeShort(packet.port); header.write(packet.data, 0, packet.length)
                    val data = framed.toByteArray()
                    local.send(DatagramPacket(data, data.size, receiverAddress)); count(packet.length)
                } catch (_: Exception) { if (local.isClosed || outbound.isClosed) break }
            }
        }
        try {
            client.soTimeout = 0
            while (open.get() && input.read() != -1) { /* TCP connection owns UDP association. */ }
        } finally {
            association.set(false); local.close(); outbound.close(); sender.cancel(true); receiver.cancel(true)
            resources.remove(local); resources.remove(outbound)
        }
    }
    override fun close() {
        open.set(false)
        resources.forEach { try { it.close() } catch (_: Exception) { } }
        pool.shutdownNow()
    }
}
