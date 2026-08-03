# CTIS262 — Applied computer networks

You are configuring devices in a simulator and proving the result with commands. There is no pseudocode here and no program to write. The deliverable is a working topology plus the verification output that shows it works. A configuration that was entered but never verified is not an answer.

## Teaching posture

Build on the topology, not on the theory. Give the address table first, then the objective, then the parts, then the numbered steps, then the verification. Every part ends by proving something with `ping`, `tracert`, or a `show` command, and the expected output is stated before the student runs it.

Say what to observe, not only what to type. When a redundant path is configured, the point is to break the primary path and watch the traffic move.

## Scope

Switch and router basics, hostnames, addressing, passwords, banners and saving, VLANs and trunking, EtherChannel, DHCP for IPv4 and IPv6, SLAAC, static and floating static routes, load balancing, Telnet and SSH, and verification with `ping`, `tracert` and the `show` family.

## Submission rules

These are graded separately from the configuration and are easy points to lose:

| Rule | Consequence |
|---|---|
| File name pattern `HW1_yourname_surname.pkt` | not following it deducts 5% of the homework grade |
| No Turkish characters in the file name | same deduction |
| Zip the saved file and upload it to the course system | required form |
| Deadline is absolute | no late submission is accepted |
| Individual work | plagiarism is penalised severely |

Save the topology before zipping. A `.pkt` that was never saved after the last change loses the configuration.

## The required shape

Every task is written and answered in the same layout. Follow it in the answer too.

```text
Topology            the diagram
Addressing Table    device | interface | IP address | subnet mask | default gateway
Objectives          what the finished network must do
Part 1: ...
    Step 1: ...
        a. ...
        b. ...
    Step 2: Verify ...
Part 2: ...
```

Fill the addressing table before touching a device. Every later step reads from it, and a mismatch between the table and the configuration is the most common cause of a failing ping.

## Skeletons

### Base device configuration

```text
Switch> enable
Switch# configure terminal
Switch(config)# hostname S1
S1(config)# no ip domain-lookup
S1(config)# enable secret class
S1(config)# line console 0
S1(config-line)# password cisco
S1(config-line)# login
S1(config-line)# logging synchronous
S1(config-line)# exit
S1(config)# line vty 0 15
S1(config-line)# password cisco
S1(config-line)# login
S1(config-line)# exit
S1(config)# service password-encryption
S1(config)# banner motd #Authorized access only#
S1(config)# end
S1# copy running-config startup-config
```

`copy running-config startup-config` at the end of every part. Configuration lives in RAM until it is saved.

### Interface addressing

```text
R1(config)# interface g0/0/0
R1(config-if)# description Link to S1
R1(config-if)# ip address 192.168.1.1 255.255.255.0
R1(config-if)# no shutdown
```

Router interfaces are administratively down by default; `no shutdown` is not optional. Switch access ports are up already.

### VLANs and trunking

```text
S1(config)# vlan 10
S1(config-vlan)# name Sales
S1(config-vlan)# exit
S1(config)# interface range f0/1-8
S1(config-if-range)# switchport mode access
S1(config-if-range)# switchport access vlan 10
S1(config-if-range)# exit
S1(config)# interface g0/1
S1(config-if)# switchport mode trunk
S1(config-if)# switchport trunk native vlan 99
```

Verify with `show vlan brief` and `show interfaces trunk`. Devices in different VLANs cannot ping each other without a router; that is the expected result, not a fault.

### EtherChannel

```text
S1(config)# interface range f0/1-2
S1(config-if-range)# channel-group 1 mode active     ! LACP
S1(config-if-range)# exit
S1(config)# interface port-channel 1
S1(config-if)# switchport mode trunk
```

Both ends must use compatible modes: `active`/`active` or `active`/`passive` for LACP, `desirable`/`auto` for PAgP. Verify with `show etherchannel summary` and read the flags: `SU` means the port channel is in use.

### DHCP for IPv4

```text
R1(config)# ip dhcp excluded-address 192.168.1.1 192.168.1.9
R1(config)# ip dhcp pool LAN1
R1(dhcp-config)# network 192.168.1.0 255.255.255.0
R1(dhcp-config)# default-router 192.168.1.1
R1(dhcp-config)# dns-server 8.8.8.8
```

Exclude the addresses you assigned statically before creating the pool. Verify with `show ip dhcp binding` and by setting the PC to DHCP and checking the address it received.

### IPv6 and SLAAC

```text
R1(config)# ipv6 unicast-routing
R1(config)# interface g0/0/0
R1(config-if)# ipv6 address 2001:db8:acad:1::1/64
R1(config-if)# ipv6 address fe80::1 link-local
```

Without `ipv6 unicast-routing` the router does not send router advertisements, so SLAAC produces nothing. Verify with `show ipv6 interface brief` and check that the host built an address from the advertised prefix.

### Static and floating static routes

```text
R1(config)# ip route 192.168.3.0 255.255.255.0 10.0.0.2
R1(config)# ip route 192.168.3.0 255.255.255.0 10.0.1.2 10
```

The second route carries a higher administrative distance, so it stays out of the table until the first path fails. That is the floating static route. Prove it in three moves: `tracert` and record the path, shut the preferred interface, `tracert` again and show the alternate path.

Equal-cost paths are configured with the same distance, and traffic to different destinations takes different links. Trace to several addresses in the target network to show the load sharing.

### Telnet and SSH

```text
R1(config)# ip domain-name ctis.local
R1(config)# crypto key generate rsa general-keys modulus 1024
R1(config)# username admin secret cisco
R1(config)# line vty 0 4
R1(config-line)# transport input ssh
R1(config-line)# login local
```

SSH needs a hostname, a domain name, and a key, in that order. `transport input ssh` alone disables Telnet, which is the point of the exercise: verify that Telnet now fails and SSH succeeds.

### Verification vocabulary

| Command | Answers |
|---|---|
| `ping` | is there end-to-end reachability |
| `tracert` / `traceroute` | which path did the traffic take |
| `show ip interface brief` | which interfaces are up with which addresses |
| `show vlan brief` | which ports are in which VLAN |
| `show interfaces trunk` | is the trunk formed, with which native VLAN |
| `show etherchannel summary` | is the port channel bundled and in use |
| `show ip route` | which routes are installed, with what distance |
| `show ip dhcp binding` | which leases were handed out |
| `show ipv6 interface brief` | which IPv6 addresses were formed |
| `show running-config` | what is actually configured right now |

## Rules with rewrites

**Configured without verifying.**
A part that ends at the last configuration line becomes one that ends with the `show` or `ping` output that proves it.

**Router interface left down.**
An `ip address` line with no follow-up becomes the same line followed by `no shutdown`.

**Configuration not saved.**
A finished part becomes one ending in `copy running-config startup-config`.

**Static addresses inside the DHCP pool.**
A pool covering the gateway address becomes one preceded by `ip dhcp excluded-address`.

**IPv6 addresses with no routing enabled.**
Interface addresses alone become the same plus `ipv6 unicast-routing` in global configuration.

**Backup route with the default distance.**
`ip route ... 10.0.1.2` becomes `ip route ... 10.0.1.2 10`, so it floats behind the primary.

**Mismatched EtherChannel modes.**
`active` on one side and `desirable` on the other becomes a matching pair from the same protocol.

**File named freely.**
`hw1.pkt` or a name with Turkish characters becomes `HW1_yourname_surname.pkt` in ASCII.

**Failover claimed but not shown.**
"The backup route works" becomes a `tracert` before, an interface shutdown, and a `tracert` after.

## Failure modes

- An addressing table filled in after configuring, so the device and the table disagree.
- A wrong subnet mask that makes two hosts appear to be on different networks.
- A default gateway missing on the host, so local pings work and remote ones do not.
- A native VLAN mismatch across a trunk, which the switch reports and which breaks the link.
- Ports added to an EtherChannel while their configurations differ, so the bundle never forms.
- Testing connectivity from the router instead of from the host the task named.
- Reading `show running-config` and assuming it is saved.
- Forgetting that the first ping after a change can fail while ARP resolves; repeat before concluding.
- Shutting the wrong interface when demonstrating failover, so the trace does not change.

## Verification

Before reporting the work as done, confirm all of these:

- The addressing table is complete and matches every configured interface.
- Every part ends with the verification the task named, and the output is included.
- Hosts in the same network ping each other; hosts in different VLANs do not without routing.
- Trunks, port channels, routes, and DHCP bindings each appear in their `show` output.
- Failover was demonstrated with a trace before and after breaking the preferred path.
- Remote access behaves as specified: SSH succeeds, Telnet fails when it was disabled.
- Every device was saved with `copy running-config startup-config`.
- The file is named `HW1_yourname_surname.pkt`, in ASCII, saved and zipped.

## Workflow

1. Copy the addressing table and fill in every blank before touching a device.
2. Configure the base settings on each device: hostname, passwords, banner, save.
3. Address the interfaces and bring the router interfaces up.
4. Work through the parts in order, one step at a time.
5. Run the verification the step names and record the output.
6. For redundancy tasks, trace, break the path, trace again.
7. Save every device and name the file exactly as required.
8. Report which verifications you ran and which you could not.
