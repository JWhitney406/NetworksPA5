'''
Created on Oct 12, 2016

@author: mwitt_000
'''
import queue
import threading


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    #  @param cost - of the interface used in routing
    #  @param capacity - the capacity of the link in bps
    def __init__(self, cost=0, maxsize=0, capacity=500):
        self.in_queue = queue.PriorityQueue(maxsize);
        self.out_queue = queue.PriorityQueue(maxsize);
        self.cost = cost
        self.capacity = capacity #serialization rate
        self.next_avail_time = 0 #the next time the interface can transmit a packet
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                priority, pkt_S = self.in_queue.get(False)
#                 if pkt_S is not None:
#                     print('getting packet from the IN queue')
                return pkt_S
            else:
                priority, pkt_S = self.out_queue.get(False)
#                 if pkt_S is not None:
#                     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        header_length = NetworkPacket.dst_addr_S_length + NetworkPacket.prot_S_length + 1
        try:
            pot_prot = int(pkt[header_length : header_length+1])
            priority = int(NetworkPacket.from_byte_S(pkt[MPLS_frame.label_length:]).priority)
        except: 
            priority = int(NetworkPacket.from_byte_S(pkt).priority)
        if in_or_out == 'out':
            self.out_queue.put((-priority, pkt), block)
        else:
            self.in_queue.put((-priority, pkt), block)
            
        
## Implements a network layer packet (different from the RDT packet 
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    ## packet encoding lengths 
    dst_addr_S_length = 5
    prot_S_length = 1
    
    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst_addr, prot_S, priority, data_S):
        self.dst_addr = dst_addr
        self.prot_S = prot_S
        self.priority = priority
        self.data_S = data_S
                
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst_addr).zfill(self.dst_addr_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += str(self.priority)
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst_addr = int(byte_S[0 : NetworkPacket.dst_addr_S_length])
        prot_S = byte_S[NetworkPacket.dst_addr_S_length : NetworkPacket.dst_addr_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            print('%s: unknown prot_S field: %s' %(self, prot_S))
        priority = byte_S[NetworkPacket.dst_addr_S_length + NetworkPacket.prot_S_length:NetworkPacket.dst_addr_S_length + NetworkPacket.prot_S_length + 1]
        data_S = byte_S[NetworkPacket.dst_addr_S_length + NetworkPacket.prot_S_length + 1: ]        
        return self(dst_addr, prot_S, priority, data_S)
    
class MPLS_frame:
    label_length = 5

    def __init__(self, label, pkt_S):
        self.lbl = label
        self.pkt_S = pkt_S

    def encapsulate(self):
        byte_S = str(self.lbl).zfill(self.label_length)
        byte_S += self.pkt_S
        return byte_S
    
    ## extract a packet from an MPLS frame in the form of a byte string
    # @param byte_S: byte string representation of the packet encased in MPLS frame
    @classmethod
    def decapsulate(self, byte_S):
        lbl = int(byte_S[ : self.label_length])
        return self(lbl, byte_S[self.label_length : len(byte_S)])
        
## Implements a network host for receiving and transmitting data
class Host:
        
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
       
    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    # @param priority: packet priority
    def udt_send(self, dst_addr, data_S, priority=0):
        p = NetworkPacket(dst_addr, 'data', priority, data_S)
        pkt_S = p.to_byte_S()
        mpls = MPLS_frame(0, pkt_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(mpls.encapsulate(), 'out') #send packets always enqueued successfully
        
    ## receive packet from the network laye
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            # l, pkt = MPLS_frame.decapsulate(pkt_S)
            print('%s: received packet "%s"' % (self, pkt_S))
       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router described in class
class Router:
    
    ##@param name: friendly router name for debugging
    # @param intf_cost_L: outgoing cost of interfaces (and interface number)
    # @param intf_capacity_L: capacities of outgoing interfaces in bps 
    # @param rt_tbl_D: routing table dictionary (starting reachability), eg. {1: {1: 1}} 
    #                packet to host 1 through interface 1 for cost 1
    # @param mpls_rt_tbl: mpls routing table for label based forwarding eg. {{1, 1}: {1: 1}} 
    #                packet with label 1 through interface 1 should be sent with a label 1 out interface 1 
    # @param max_queue_size: max queue length (passed to Interface)

    def __init__(self, name, intf_cost_L, intf_capacity_L, rt_tbl_D, mpls_rt_tbl, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        #note the number of interfaces is set up by out_intf_cost_L
        assert(len(intf_cost_L) == len(intf_capacity_L))
        self.intf_L = []
        for i in range(len(intf_cost_L)):
            self.intf_L.append(Interface(intf_cost_L[i], max_queue_size, intf_capacity_L[i]))
        #set up the routing table for connected hosts
        self.rt_tbl_D = rt_tbl_D
        self.mpls_rt_tbl = mpls_rt_tbl

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                mpls = MPLS_frame.decapsulate(pkt_S)  #parse a packet out
                l = mpls.lbl
                p = NetworkPacket.from_byte_S(mpls.pkt_S)
                if p.prot_S == 'data':
                    self.forward_packet(l,p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
            
    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, l, p, i):
        try:
            l2, intf = self.mpls_rt_tbl.get((l,i))
            pkt = p.to_byte_S()
            mpls = MPLS_frame(l2, pkt)
            if not((self.name == 'D' and intf == 2) or 
                   (self.name == 'A' and (intf == 0 or intf == 1))):
                pkt_S = mpls.encapsulate()
                self.intf_L[intf].put(pkt_S, 'out', True)
                print('%s: forwarding packet "%s" from interface %d to %d' % (self, pkt_S, i, intf))
            else:
                self.intf_L[intf].put(pkt, 'out', True)
                print('%s: forwarding packet "%s" from interface %d to %d' % (self, pkt, i, intf))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass
        
    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        #TODO: add logic to update the routing tables and
        # possibly send out routing updates
        print('%s: Received routing update %s from interface %d' % (self, p, i))
        
    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # a sample route update packet
        p = NetworkPacket(0, 'control', 'Sample routing table packet')
        try:
            #TODO: add logic to send out a route update
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass
   
    """    
    ## Print routing table
    def print_routes(self):
        print('%s: routing table' % self)
        #TODO: print the routes as a two dimensional table for easy inspection
        # Currently the function just prints the route table as a dictionary
        print(self.rt_tbl_D)
    """ 
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 
