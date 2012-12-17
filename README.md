Modshaft
========

This python application lets you tunnel arbitrary ethernet traffic over the Modbus/TCP protocol.  It is meant to assist in evading application layer firewalls.  By running a special device (such a PwnPlug) on the PLC end of a control system network and running this tool, you may pass arbitrary traffic through to the PLC network, thereby evading an application-layer firewall.  To the firewall, your traffic will appear to be 'read holding register' commands.

Run modbus-server.py on a system 'behind' a Modbus application-layer firewall, on the PLC side of the control network.

Run modbus-client.py on your workstation network.

Currently IP addresses, ports, etc are all hard-coded, sorry about that.  Things aren't particularly well-written in general at the moment, but the tunnel does work.  Expect an additional ~150ms latency, and not a lot of bandwidth.  You might also want to adjust the MTU downwards: a packet full of modbus commands can only squeeze 3 bytes per modbus frame of meaningful data using the 'read registers' command, so setting the MTU of both client and server tap interfaces to something small (400 bytes or less) will probably increase the efficiency of the protocol a lot, and cause fewer tcp retransmissions.  In addition you may want to set adjust your tcp timeouts upwards slightly for the tap interfaces on both ends of the tunnel.

Questions or comments?  Please try krwightm 'at' gmail dot com.

