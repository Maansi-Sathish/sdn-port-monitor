"""
Port Status Monitoring Tool - POX Controller
Monitors switch port up/down events, logs changes, and displays status.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from datetime import datetime

log = core.getLogger()

port_status_db = {}
LOG_FILE = "/tmp/port_status_log.txt"


def log_event(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    log.info(full_msg)
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")


class PortMonitor(EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        self.mac_table = {}
        log_event("PortMonitor started. Listening for switch events...")

    def _handle_ConnectionUp(self, event):
        dpid = dpidToStr(event.dpid)
        log_event(f"Switch CONNECTED: {dpid}")
        if event.dpid not in port_status_db:
            port_status_db[event.dpid] = {}
        msg = of.ofp_stats_request(body=of.ofp_port_stats_request())
        event.connection.send(msg)
        fm = of.ofp_flow_mod()
        fm.priority = 1
        fm.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
        event.connection.send(fm)

    def _handle_ConnectionDown(self, event):
        dpid = dpidToStr(event.dpid)
        log_event(f"ALERT: Switch DISCONNECTED: {dpid}")

    def _handle_PortStatus(self, event):
        dpid = dpidToStr(event.dpid)
        port = event.ofp.desc
        port_no = port.port_no
        port_name = port.name.decode() if isinstance(port.name, bytes) else port.name
        reason_map = {
            of.OFPPR_ADD: "ADDED",
            of.OFPPR_DELETE: "DELETED",
            of.OFPPR_MODIFY: "MODIFIED"
        }
        reason = reason_map.get(event.ofp.reason, "UNKNOWN")
        is_down = bool(port.config & of.OFPPC_PORT_DOWN) or \
                  bool(port.state & of.OFPPS_LINK_DOWN)
        status = "DOWN" if is_down else "UP"
        if event.dpid not in port_status_db:
            port_status_db[event.dpid] = {}
        port_status_db[event.dpid][port_no] = status
        msg = (f"Switch {dpid} | Port {port_no} ({port_name}) | "
               f"Reason: {reason} | Status: {status}")
        log_event(msg)
        if status == "DOWN":
            log_event(f"*** ALERT *** Port {port_name} on switch {dpid} is DOWN!")
        display_port_status(event.dpid)

    def _handle_PacketIn(self, event):
        packet = event.parsed
        dpid = event.dpid
        in_port = event.port
        if dpid not in self.mac_table:
            self.mac_table[dpid] = {}
        self.mac_table[dpid][packet.src] = in_port
        if packet.dst in self.mac_table.get(dpid, {}):
            out_port = self.mac_table[dpid][packet.dst]
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, in_port)
            msg.idle_timeout = 30
            msg.hard_timeout = 60
            msg.priority = 10
            msg.data = event.ofp
            msg.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg)
        else:
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.in_port = in_port
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            event.connection.send(msg)


def display_port_status(dpid=None):
    log.info("===== Current Port Status =====")
    if dpid and dpid in port_status_db:
        for port_no, status in port_status_db[dpid].items():
            log.info(f"  Switch {dpidToStr(dpid)} | Port {port_no}: {status}")
    else:
        for d, ports in port_status_db.items():
            for port_no, status in ports.items():
                log.info(f"  Switch {dpidToStr(d)} | Port {port_no}: {status}")
    log.info("================================")


def launch():
    core.registerNew(PortMonitor)
    log.info("Port Status Monitoring Tool loaded.")
