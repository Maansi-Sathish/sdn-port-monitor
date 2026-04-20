"""
Custom Mininet Topology for Port Status Monitoring
3 switches, 6 hosts (2 per switch), connected in a line
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink
import time


class MonitorTopo(Topo):
    def build(self):
        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        h5 = self.addHost('h5', ip='10.0.0.5/24')
        h6 = self.addHost('h6', ip='10.0.0.6/24')

        # Connect hosts to switches
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s2)
        self.addLink(h4, s2)
        self.addLink(h5, s3)
        self.addLink(h6, s3)

        # Connect switches in a line
        self.addLink(s1, s2)
        self.addLink(s2, s3)


def run():
    topo = MonitorTopo()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=RemoteController('c0', ip='127.0.0.1', port=6633),
        link=TCLink,
        autoSetMacs=True
    )

    net.start()
    info("*** Topology started\n")
    info("*** Hosts: h1-h6 | Switches: s1, s2, s3\n")
    info("*** Try: pingall, h1 ping h6, link s1 s2 down/up\n")
    
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
