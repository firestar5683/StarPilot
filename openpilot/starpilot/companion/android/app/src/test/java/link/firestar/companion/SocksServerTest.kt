package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test
import java.io.*
import java.net.*
import java.util.concurrent.atomic.AtomicLong

class SocksServerTest {
    private val loop = InetAddress.getByName("127.0.0.1") as Inet4Address
    private val publicIp = InetAddress.getByName("93.184.216.34")
    private class Transport(val remote: InetSocketAddress, val address: InetAddress) : CellularTransport {
        val lookups = mutableListOf<String>()
        override fun resolve(host: String): Array<InetAddress> { lookups.add(host); return arrayOf(address) }
        override fun socket(): Socket = object : Socket() {
            override fun connect(endpoint: SocketAddress, timeout: Int) { super.connect(remote, timeout) }
        }
        override fun datagram(): DatagramSocket = object : DatagramSocket() {
            override fun send(packet: DatagramPacket) { packet.socketAddress = remote; super.send(packet) }
            override fun receive(packet: DatagramPacket) { super.receive(packet); packet.address = address }
        }
    }
    private fun authenticate(socket: Socket, password: String = "password"): DataInputStream {
        socket.soTimeout = 2000
        val output = DataOutputStream(socket.getOutputStream())
        val input = DataInputStream(socket.getInputStream())
        output.write(byteArrayOf(5, 1, 2)); output.flush()
        assertEquals(5, input.readUnsignedByte()); assertEquals(2, input.readUnsignedByte())
        output.writeByte(1); output.writeByte(4); output.writeBytes("user"); output.writeByte(password.length); output.writeBytes(password); output.flush()
        assertEquals(1, input.readUnsignedByte()); assertEquals(if (password == "password") 0 else 1, input.readUnsignedByte())
        return input
    }
    private fun request(socket: Socket, command: Int, host: String, port: Int) {
        val output = DataOutputStream(socket.getOutputStream())
        output.write(byteArrayOf(5, command.toByte(), 0, 3, host.length.toByte()))
        output.writeBytes(host); output.writeShort(port); output.flush()
    }
    private fun response(input: DataInputStream, code: Int = 0): Int {
        assertEquals(5, input.readUnsignedByte()); assertEquals(code, input.readUnsignedByte()); assertEquals(0, input.readUnsignedByte())
        assertEquals(1, input.readUnsignedByte()); input.readInt(); return input.readUnsignedShort()
    }
    @Test fun domainConnectResolvesThroughCellularAndCountsBothDirections() {
        ServerSocket(0, 1, loop).use { remote ->
            val echo = Thread { remote.accept().use { socket -> val value = socket.getInputStream().read(); socket.getOutputStream().write(value) } }
            echo.start()
            val transport = Transport(InetSocketAddress(loop, remote.localPort), publicIp)
            val bytes = AtomicLong()
            SocksServer(loop, transport, "user", "password", { bytes.addAndGet(it.toLong()) }, "127.0.0.1", 0).use { server ->
                Socket(loop, server.port).use { socket ->
                    val input = authenticate(socket)
                    request(socket, 1, "api.mapbox.com", 443); response(input)
                    socket.getOutputStream().write(42)
                    assertEquals(42, input.read())
                    assertEquals(listOf("api.mapbox.com"), transport.lookups)
                    assertEquals(2L, bytes.get())
                }
            }
            echo.join(2000); assertFalse(echo.isAlive)
        }
    }
    @Test fun invalidCredentialsAndUploadHostsAreRejected() {
        val transport = Transport(InetSocketAddress(loop, 1), publicIp)
        SocksServer(loop, transport, "user", "password", {}, "127.0.0.1", 0).use { server ->
            Socket(loop, server.port).use { socket -> assertEquals(-1, authenticate(socket, "wrong").read()) }
            Socket(loop, server.port).use { socket ->
                val input = authenticate(socket)
                request(socket, 1, "upload.comma.ai", 443); response(input, 4)
                assertTrue(transport.lookups.isEmpty())
            }
        }
    }
    @Test fun udpAssociationRelaysAndClosesWithControlSocket() {
        DatagramSocket(InetSocketAddress(loop, 0)).use { remote ->
            remote.soTimeout = 3000
            val echo = Thread {
                val packet = DatagramPacket(ByteArray(512), 512); remote.receive(packet); remote.send(packet)
            }
            echo.start()
            val transport = Transport(InetSocketAddress(loop, remote.localPort), publicIp)
            SocksServer(loop, transport, "user", "password", {}, "127.0.0.1", 0).use { server ->
                Socket(loop, server.port).use { control ->
                    val input = authenticate(control)
                    request(control, 3, "0.0.0.0", 0)
                    val port = response(input)
                    DatagramSocket(InetSocketAddress(loop, 0)).use { udp ->
                        udp.soTimeout = 2000
                        val frame = ByteArrayOutputStream()
                        DataOutputStream(frame).apply {
                            writeShort(0); writeByte(0); writeByte(3); writeByte(14); writeBytes("api.mapbox.com")
                            writeShort(remote.localPort); writeBytes("hello")
                        }
                        // 14 includes the dot-separated hostname length.
                        val data = frame.toByteArray()
                        udp.send(DatagramPacket(data, data.size, loop, port))
                        val packet = DatagramPacket(ByteArray(512), 512); udp.receive(packet)
                        assertEquals("hello", packet.data.copyOfRange(10, packet.length).toString(Charsets.UTF_8))
                    }
                }
            }
            echo.join(2000); assertFalse(echo.isAlive)
        }
    }
}
