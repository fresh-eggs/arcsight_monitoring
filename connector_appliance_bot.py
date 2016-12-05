from multiprocessing import Lock
from datetime import datetime
import time
import threading
import os
from contextlib import contextmanager
import sys
import socket
import random
import datetime
import json


#=================================
#  Custom Classes.
#=================================
class Container(object):

        def __init__(self, num_agents, num_destinations, id, state):
                self.ID = id
                self.STATE = state
                self.num_of_agents = num_agents
                self.num_of_destinations = num_destinations
                self.agents=[]
                self.destinations=[]
                self.eps = 0
                self.throughput = 0
                self.queue_drop = 0.0

        def setID(self, id):
                self.ID = id

        def getID(self):
                return self.ID

        def setNumAgents(self, num):
                self.num_of_agents = num

        def getNumAgents(self):
                return self.num_of_agents

        def setNumDestinations(self, num):
                self.num_of_destinations = num

        def getNumDestinations(self):
                return self.num_of_destinations

        def setSTATE(self, state):
                self.STATE = state

        def getSTATE(self):
                return self.STATE

        def setEPS(self, eps_param):
                self.eps = eps_param

        def getEPS(self):
                return self.eps

        def setThroughput(self, throughput_param):
                self.throughput = throughput_param

        def getThroughput(self):
                return self.throughput

        def setQueueDrop(self, drop):
                self.queue_drop = drop

        def getQueueDrop(self):
                return self.queue_drop

        def __iter__(self):
                return self

        def next(self):
                next_value = self
                return next_value


#============
#  GLOBALS
#============
ZABBIX_SERVER = ""
path = ""
lock = threading.Semaphore(10)
CONTAINERS=[]

#Spin up a bunch of containers
c_1 = Container(0, 0, 1, "EMPTY")
c_2 = Container(0, 0, 2, "EMPTY")
c_3 = Container(0, 0, 3, "EMPTY")
c_4 = Container(0, 0, 4, "EMPTY")
c_5 = Container(0, 0, 5, "EMPTY")
c_6 = Container(0, 0, 6, "EMPTY")
c_7 = Container(0, 0, 7, "EMPTY")
c_8 = Container(0, 0, 8, "EMPTY")


#======================
#  Utility Functions
#======================
#simple utility function to quickly update zabbix about the state of the container.
def containerStateQuickSend(conn_ID, conn_state):
        query = ("zabbix_sender -z %s -p 10051 -s %s -k c_%s.state -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], conn_ID, conn_state))
        sender_results = os.popen(query).read()


#update the log for this particular container.
def containerLogUpdate(conn_ID, log_msg):
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        log = "["+st+"]: "+log_msg


#update our list of non-empty containers
def updateContainerList():
        #define global
        global CONTAINERS
        global c_1, c_2, c_3, c_4, c_5, c_6, c_7, c_8

        #create a temporary list of the containers so we can itterate thorugh them.
        temp_list=[]; temp_list.append(c_1); temp_list.append(c_2); temp_list.append(c_3); temp_list.append(c_4); temp_list.append(c_5); temp_list.append(c_6); temp_list.append(c_7); temp_list.append(c_8);

        #append the non empty containers to our list.
        for container in temp_list:
                #check to see if this container is empty
                has_connector = hasConnector(container)
                if has_connector == True:
                        CONTAINERS.append(container)
                else:
                        try:
                                CONTAINERS.remove(container)
                        except Exception,e:
                                print e


#Here we are interested in gathering the number of agents on this container, along with
#particular information about the destinations. NOTE: In order to have new destinations
#picked up, simply restart the script.
def getContainerInfo():
        #define global
        global CONTAINERS
        global c_1, c_2, c_3, c_4, c_5, c_6, c_7, c_8

        try:
                for container in CONTAINERS:
                        #gather the number of configured agents across per container.
                        conn_ID = container.getID()
                        query = ("cat "+path+str(conn_ID)+"/current/user/agent/agent.properties | grep agents.maxAgents=")
                        result = os.popen(query).read() #<- provides stdout of the os call.
                        num = result.split("agents.maxAgents=", 1)[1].strip()
                        container.setNumAgents(int(num))
                        #append the agents to the container object.
                        for i in range(0, int(num)):
                                container.agents.append(i)

                #count the total number of agents we just collected for each container.
                NUM_OF_AGENTS = 0
                for container in CONTAINERS:
                        NUM_OF_AGENTS += container.getNumAgents()

                #For each of the containers, add an entry to our discovery string for each of the agents.
                #Check if we are on the last entry as it will need to be formated differently.
                num_agents = NUM_OF_AGENTS
                json = ("{ \"data\": [")
                for container in CONTAINERS:
                        i = 0
                        while i < int(container.getNumAgents()):
                                #this checks for the case where we are adding the last entry to our JSON string.
                                #This is important as our last elements needs to be fromated differently.
                                if (int(num_agents) - 1) > 0:
                                        json += ("{\"{#AGENT}\": \"%s\", \"{#ID}\": \"%s\"}, " % (str(i), container.getID()))
                                        i+=1
                                        num_agents-=1
                                #if this is the last element, do not include the ,
                                else:
                                        json += ("{\"{#AGENT}\": \"%s\", \"{#ID}\": \"%s\"}" % (str(i), container.getID()))
                                        i+=1
                                        num_agents-=1

                #stick the end of the string on, then send the json structure to the discovery rule.
                json += "]}"
                query = ("zabbix_sender -z %s -s %s -k \"agent_discovery\" -o \'%s\'" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(json)))
                os.system(query)

                #now we loop through each agent, checking their destinations and building a list of unique destinations.

                NUM_OF_DESTINATIONS_TOTAL = 0
                for container in CONTAINERS:
                        i = 0
                        while i < int(container.getNumAgents()):
                                query = ("cat "+path+str(container.getID())+"/current/user/agent/agent.properties | grep \"agents\[%s\].destination.count=\"" % str(i))
                                result = os.popen(query).read() #<- provides stdout of the os call.

                                #get number of destinations for that agent
                                agent_destinations = 0
                                agent_destinations = int(result.split("agents["+str(i)+"].destination.count=", 1)[1])

                                #Loop through each destination entry for this agent, adding the unique destination host names to our array.
                                q = 0
                                while q < agent_destinations:
                                        query = ("cat "+path+str(container.getID())+"/current/user/agent/agent.properties | grep \"agents\[%s\].destination\[%s\].params=\"" % (str(i), str(q)))
                                        result = os.popen(query).read() #<- provides stdout of the os call.

                                        #split out the hostname
                                        destination_hostname = str(result.split("<Parameter Name\=\"host\" Value\=\"", 1)[1].split("\"/>\\n",1)[0]).strip()

                                        #append this hostname to our master list if not already present.
                                        if destination_hostname not in container.destinations:
                                                container.destinations.append(destination_hostname)
                                                container.setNumDestinations(container.getNumDestinations() +1)
                                                NUM_OF_DESTINATIONS_TOTAL += 1
                                        q+=1
                                i+=1

                #with the list built, craft a JSON request that we will send to the DestinationDiscovery in zabbix.
                #we are not worried about duplicates as zabbix is smart enough to not add a duplicate key.]
                json = ("{ \"data\": [")
                for container in CONTAINERS:
                        for dest in container.destinations:
                                #if this is the last element, do not include the ','
                                if (int(NUM_OF_DESTINATIONS_TOTAL) - 1) > 0:
                                        json += ("{\"{#DESTINATION}\": \"%s\", \"{#ID}\": \"%s\"}, " % (dest, container.getID()))
                                        NUM_OF_DESTINATIONS_TOTAL-=1
                                #if this is not the last element, include the ',' for json format
                                else:
                                        json += ("{\"{#DESTINATION}\": \"%s\", \"{#ID}\": \"%s\"}" % (dest, container.getID()))
                                        NUM_OF_DESTINATIONS_TOTAL-=1

                #stick the end of the string on, then send the json structure to the discovery rule.
                json += "]}"
                query = ("zabbix_sender -z %s -s %s -k \"destination_discovery\" -o \'%s\'" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(json)))
                os.system(query)
        except Exception,e:
                print e


#this function is simply used to determine if a container is empty or not.
def hasConnector(container):
        try:
                #check if this container has a connector by checking for the existance of the appropriate dir
                #calling it in the while loop allows for discovery of new connectors without restart of the script.
                query = ("cat "+path+str(container.getID())+"/current/user/agent/agent.properties | grep agentid")
                result = os.popen(query).read() #<- provides stdout of the os call.
                agents = result.split("\n", 1)

                #start off considering it as empty, only change if proven wrong!
                #Here we check each agentID for a corresponding XML file that has something in it other than "Temporary Connector".
                #this tell us that there is at least one real agent in the container, therefore it is not empty.
                has_connector = False
                for line in agents:
                        if line != '':
                                try:
                                        agent_id = line.split("agentid=", 1)[1].split("\=\=", 1)[0] #parse out the result
                                        query = ("cat "+path+str(container.getID())+"/current/user/agent/"+agent_id+"==.xml")
                                        result = os.popen(query).read() #<- provides stdout of the os call.
                                except:
                                        continue

                                if result != "Temporary Connector":
                                        has_connector = True
                                        break

                return has_connector
        except Exception:
                return False



#===========================
#  Bot Operation Functions
#===========================
#This function is dedicated to gathering information about services on a timeout basis.
#It is also where we place any custom checks on a timeout basis. To add a custom check,
#simply add a timeout on the interval you would like, then add the check logic under the
#conditional statement for your timeout.
def connectorApplianceServices():
        #Set timeout
        timeout = time.time() + 60*5   # 5 minutes from now

        while 1:
                #=======================
                #       SERVICES

                #Call on monit and grab the output
                query = ("/opt/local/monit/bin/monit status")
                status_info = os.popen(query).read() #<- provides stdout of the os call.

                #split up the output by services (they happen to be seperated by blank spaces)
                services = status_info.split("\n\n")

                #Parse out from each block of text what we want to know about the service.
                for service in services[1:8]:
                        #parse the service name
                        service_name = service.split("'", 1)[1].split("'", 1)[0]

                        #parse the status
                        status = service.split("status                            ", 1)[1].split("monitoring status", 1)[0]
                        query = ("zabbix_sender -z %s -p 10051 -s %s -k %s.status -o \"%s\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], service_name, status))
                        os.system(query)


                #have we run out of time to consider it dead?
                if time.time() > timeout:
                        #=======================
                        #       HARDWARE

                        #ensure the binary we need is on the machine.
                        has_hplog = os.path.isfile("/sbin/hplog")

                        if has_hplog == True:
                                #check for POWER issue
                                query=("/sbin/hplog -p | grep -e \"Failed\" ")
                                power_info = os.popen(query).read()
                                if power_info != "":
                                        #there is an issue to report
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.psu -o \"PROBLEM\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                                else:
                                        #system looks ok
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.psu -o \"OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)

                                #check for FAN issue
                                #normal output:
                                #1  Var. Speed   System Board    Normal     Yes     Normal   ( 13)
                                query = ("/sbin/hplog -f | grep -e \"Failed\" ")
                                fan_info = os.popen(query).read()
                                if fan_info != "":
                                        #there is an issue to report
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.fan -o \"PROBLEM\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                                else:
                                        #system looks ok
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.fan -o \"OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)

                                #check for TEMPERATURE issue
                                query = ("/sbin/hplog -t | grep -e \"Critical\" ")
                                temp_info = os.popen(query).read()
                                if temp_info != "":
                                        #there is an issue to report
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.temp -o \"PROBLEM\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                                else:
                                        #system looks ok
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.temp -o \"OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                        else:
                                query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.psu -o \"hp_log-not-found\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                os.system(query)
                                query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.temp -o \"hp_log-not-found\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                os.system(query)
                                query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.fan -o \"hp_log-not-found\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                os.system(query)


                        #check for logical HDD issues.
                        query = ("hpacucli controller slot=0 logicaldrive all show status")
                        hdd_info = os.popen(query).read()
                        if "logicaldrive" in hdd_info:
                                try:
                                        logical_status = hdd_info.split("): ", 1)[1].split("\n", 1)[0]
                                except:
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.logical -o \"NO-STATUS\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)

                                if logical_status == "OK":
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.logical -o \"OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                                else:
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.logical -o \"NOT-OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                        else:
                                query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.logical -o \"NO-STATUS\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                os.system(query)

                        #check for physical HDD issues.
                        try:
                                #ensure that our dump file exists. If not, create it.
                                if os.path.exists('/home/Script/zabbix_bot/hdd.log') == False:
                                        open('/home/Script/zabbix_bot/hdd.log', 'w').close()

                                #dump results to a file.
                                query = ("hpacucli ctrl all show config > /home/Script/zabbix_bot/hdd.log")
                                os.system(query)

                                #check for results that are not OK.
                                query = ("egrep -vie \"OK|SEP|Recovering\" /home/Script/zabbix_bot/hdd.log |grep -i \"physicaldrive\"|sed \'s/^.\{6\}//g\'")
                                os.system(query)
                                response = os.popen(query).read()

                                #report on the status.
                                if response != '':
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.physical -o \"NOT-OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                                else:
                                        query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.physical -o \"OK\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                        os.system(query)
                        except:
                                query = ("zabbix_sender -z %s -p 10051 -s %s -k hardware.hdd.physical -o \"NO-STATUS\"" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0]))
                                os.system(query)

                        timeout = time.time() + 60*5   # 5 minutes from now

                #pace yourself
                time.sleep(60)



#Here we scrape all the information from the logs. This step is called by a container thread so it simply passes some information
#as parameters to the function so it can run through each agent and each destination, gathering the required info.
def zabbixSender(conn_ID, conn_destinations, conn_agents, container):
        old_entry = None
        container.setEPS(0.0)
        container.setThroughput(0.0)

        #loop through agents, scraping their information throuhg the greps
        for agent in conn_agents:
                old_entry = False

                try:
                        #find the most recently modified agent.log file
                        query = ("find "+path+"%s/current/logs/ -name \"agent.log*\" -printf \"%%T@ %%Tc %%p\\n\" | sort -n | tail -n1" % conn_ID)
                        result = os.popen(query).read().strip()
                        log_name = result.split(path+"%s/current/logs/" % conn_ID, 1)[1]

                        #get agent information
                        query = ("cat "+path+"%s/current/logs/%s | grep -A 1 \"Agent \[%s\] status:\" | tail -n1" % (conn_ID, log_name, str(agent)))
                        agent_info = os.popen(query).read()

                        #Verify that the timestamp on the status information is not older than 5 mintues
                        result = agent_info.split(",", 1)[0].split("[", 1)[1]
                        status_time = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S") #timestamp of status information

                        query = ("date +\"%Y-%m-%d %H:%M:%S\"")
                        result = os.popen(query).read().strip()
                        sys_time = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S") #system time

                        difference = sys_time - status_time

                        #if the data is older than 5 minutes, do not update zabbix so we hit the timeout trigger.
                        if(difference.seconds) > 300:
                                old_entry = True
                                epoch = time.time()
                                stamp = datetime.datetime.fromtimestamp(epoch).strftime('%c')
                                print str(stamp)+ " | Conn: "+str(conn_ID)+" Agent: "+str(agent)+" Entry Too Old."
                                return
                except:
                        epoch = time.time()
                        stamp = datetime.datetime.fromtimestamp(epoch).strftime('%c')
                        print str(stamp)+ " | Conn: "+str(conn_ID)+" Agent: "+str(agent)+" Could not determine age."

                if(old_entry == False):
                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                agent_type = str(agent_info.split("Agent Type=", 1)[1].split(", Agent Version=", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'type.[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(agent), conn_ID, agent_type))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                agent_version = str(agent_info.split("Agent Version=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'version.[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(agent), conn_ID, agent_version))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                EPS = float(agent_info.split("Events/Sec=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'eps.[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(agent), conn_ID, EPS))
                                os.system(query)
                                container.setEPS(container.getEPS() + EPS) #sum the EPS per agent.
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                thread_count = str(agent_info.split("activeThreadCount=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'threads.[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(agent), conn_ID, thread_count))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                thread_count = str(agent_info.split("Queue Rate=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'queue_rate.[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(agent), conn_ID, thread_count))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.e
                        try:
                                queue_drop = str(agent_info.split("Queue Drop Count=", 1)[1].split(", ", 1)[0])
                                #calcualte the difference in drop then send the change to zabbix.
                                last_drop = float(container.getQueueDrop()) #get the old value
                                diff = float(queue_drop) - last_drop #calculate diff
                                container.setQueueDrop(queue_drop) #update the drop count.
                                if diff < 0.0:
                                        diff = 0.0
                                print diff
                                print last_drop
                                print queue_drop
                                query = ("zabbix_sender -z %s -s %s -k \'drop.[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(agent), conn_ID, str(diff)))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue



        #loop through the unique destinations in DESTINATIONS array, scraping their information.
        for destination in conn_destinations:
                old_entry = False
                try:
                        #get destination information using the most recent log file we found earlier
                        query = ("cat "+path+"%s/current/logs/%s | grep \"\[logStatus\] {AddrBasedSysZonePopEvents\" | grep %s | tail -n1" % (conn_ID, log_name, destination))
                        dest_info = os.popen(query).read()

                        #Verify that the timestamp on the status information is not older than 5 mintues
                        result = dest_info.split(",", 1)[0].split("[", 1)[1]
                        status_time = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S") #timestamp of status information

                        query = ("date +\"%Y-%m-%d %H:%M:%S\"")
                        result = os.popen(query).read().strip()
                        sys_time = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S") #system time

                        difference = sys_time - status_time

                        if(difference.seconds) > 300:
                                return
                except:
                        old_entry = True
                        continue

                if (old_entry == False):
                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                dest_drop_count = str(dest_info.split("Current Drop Count=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'drop[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(destination), conn_ID, dest_drop_count))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                cache_size = str(dest_info.split("Estimated Cache Size=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'cache[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(destination), conn_ID, cache_size))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                status = str(dest_info.split("status=", 2)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'status[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(destination), conn_ID, status))
                                os.system(query)
                        except IndexError:
                                #log the occurence
                                continue

                        #scrape all the elements we are interested in, sending them to zabbix.
                        try:
                                throughput = str(dest_info.split("throughput=", 1)[1].split(", ", 1)[0])
                                query = ("zabbix_sender -z %s -s %s -k \'throughput[%s, %s]\' -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], str(destination), conn_ID, throughput))
                                os.system(query)
                                container.setThroughput(container.getThroughput() + float(throughput)) #update throughput
                        except IndexError:
                                #log the occurence
                                continue


        #Send off the current status of this container as far as the script is concerend.
        command = ("ps -ef|grep connector_%s|cut -c1-100|grep -v grep |wc -l" % conn_ID)
        number_of_procs_for_container = os.popen(command).read()
        query = ("zabbix_sender -z %s -p 10051 -s %s -k c_%s.process_count -o %s" % (ZABBIX_SERVER, socket.gethostname().split(".", 1)[0], conn_ID, number_of_procs_for_container))
        sender_results = os.popen(query).read()


#get the state of the current container.
def checkStatus(container):

        #this is our check for containers that are already down. Only attempt to restart it again once every 5 minutes
        #once we report it as being DOWN.
        if container.getSTATE() == "DOWN":
                #Use HP Provided script to check the status of the Agent for this container.
                time.sleep(180) #5 minutes
                try:
                        #build and execute the query.
                        query = (path+str(container.getID())+"/current/bin/arcsight agentup")
                        result = os.popen(query).read() #<- provides stdout of the os call.

                        #now check out the answer we got to determine status
                        if "Agents are NOT running" in result:
                                containerStateQuickSend(container.getID(), "DOWN")
                                container.setSTATE("DOWN")
                        elif "Agents are running" in result:
                                containerStateQuickSend(container.getID(), "UP")
                                container.setSTATE("UP")
                        else:
                                containerStateQuickSend(container.getID(), "Could-not-get-state")
                except:
                        containerStateQuickSend(container.getID(), "Could-not-get-state")

        #This is our check for all other container states.
        else:
                #Use HP Provided script to check the status of the Agent for this container.
                try:
                        #build and execute the query.
                        query = (path+str(container.getID())+"/current/bin/arcsight agentup")
                        result = os.popen(query).read() #<- provides stdout of the os call.

                        #now check out the answer we got to determine status
                        if "Agents are NOT running" in result:
                                containerStateQuickSend(container.getID(), "MONITORING")
                                container.setSTATE("MONITORING")
                        elif "Agents are running" in result:
                                containerStateQuickSend(container.getID(), "UP")
                                container.setSTATE("UP")
                        else:
                                containerStateQuickSend(container.getID(), "Could-not-get-state")
                except:
                        containerStateQuickSend(container.getID(), "Could-not-get-state")



#When we see that a container is down, we keep polling it a few times for one mintue to ensure that it is in fact dead.
def monitor(container):
        #set timeout / path
        timeout = time.time() + 60*5

        # monitor
        while 1:
                #slow your horses
                time.sleep(30)

                #now ask the container if its agents are running. Only change state if they report themselves as running again.
                try:
                        query = (path+str(container.getID())+"/current/bin/arcsight agentup")
                        result = os.popen(query).read() #<- provides stdout of the os call.

                        #now check out the answer we got to determine status
                        if "Agents are NOT running" in result:
                                containerStateQuickSend(container.getID(), "MONITORING")
                        elif "Agents are running" in result:
                                containerStateQuickSend(container.getID(), "UP")
                                container.setSTATE("UP")
                                return
                        else:
                                containerStateQuickSend(container.getID(), "Could-not-get-state")
                                return
                except:
                        containerStateQuickSend(container.getID(), "Could-not-get-state")
                        return


                #have we run out of time to consider it dead?
                if time.time() > timeout:
                        #send email saying connector X container Y is down and we are trying to autofix
                        containerStateQuickSend(container.getID(), "DOWN")
                        container.setSTATE("DOWN")
                        return



#The main worker thread, simply polls the container for stats and monitors them.
#Ex: Read the reported EPS, if its > 0 do nothing, howver if its <= 0, throw it into the monitors function and see if
#it stays at 0 for 5 minutes.
def containerWatch(container):

        #main loop, poll the container for info, parse out what we need. (forever_)
        while 1:
                #here is where we grab all information realted to the agents and destinations for that conainer.
                has_connector = hasConnector(container)
                if has_connector == True:
                        #aquire the lock that is shared between these processes. Also make sure we wont overload with JVM threads.
                        lock.acquire()

                        #here we poll the agentup script in order to ask it is the agents are running.
                        checkStatus(container)

                        #gather information about the agents and destinations.
                        zabbixSender(container.getID(), container.destinations, container.agents, container)

                        #release the lock to allow the queue through.
                        lock.release()

                        #If the container's state returned that it is not running, begin the restart process for that container.
                        if container.getSTATE() == "MONITORING":
                                monitor(container)

                        #pace this thread.
                        time.sleep(60)

                #confirm that there is nothing in the folder that represents that container
                else:
                        # this thread has no container to watch so it can sleep for a while.
                        container.setSTATE("EMPTY")
                        containerStateQuickSend(container.getID(), container.getSTATE())
                        time.sleep(300)
                        #check to see if this container is empty
                        has_connector = hasConnector(container)
                        updateContainerList()


#=================================
#  Main.
#=================================
#Create a process for each container and set their initial states.
#We also start a thread that manages all external shell scripts.
try:
        sys.stdout = open("/home/Script/zabbix_bot/dump" + ".log", "a")
        sys.stderr = open("/home/Script/zabbix_bot/dump" + ".error", "a")
        if __name__ == '__main__':

                #set the root path where all the connectors can be found.
                path = ("/opt/arcsight/connector_")


                #here we are crafting a priliminary list of the non-empty containers (those that we will scarpe the agent.properties file)
                #create a temporary list of the containers so we can itterate thorugh them.
                temp_list=[]; temp_list.append(c_1); temp_list.append(c_2); temp_list.append(c_3); temp_list.append(c_4); temp_list.append(c_5); temp_list.append(c_6); temp_list.append(c_7); temp_list.append(c_8);

                #append the non empty containers to our list.
                for container in temp_list:
                        #initiate all connectors as emtpy in the eyes of zabbix. Allow the check to prove
                        #that assumption wrong.
                        containerStateQuickSend(container.getID(), container.getSTATE())
                        
                        #check to see if this container is empty
                        has_connector = hasConnector(container)
                        if has_connector == True:
                                CONTAINERS.append(container)

                #run the discovery rules check for each container
                getContainerInfo()

                #start threads for each of the containers
                p1 = threading.Thread(target=containerWatch, args=(c_1,))
                p1.start()

                p2 = threading.Thread(target=containerWatch, args=(c_2,))
                p2.start()

                p3 = threading.Thread(target=containerWatch, args=(c_3,))
                p3.start()

                p4 = threading.Thread(target=containerWatch, args=(c_4,))
                p4.start()

                p5 = threading.Thread(target=containerWatch, args=(c_5,))
                p5.start()

                p6 = threading.Thread(target=containerWatch, args=(c_6,))
                p6.start()

                p7 = threading.Thread(target=containerWatch, args=(c_7,))
                p7.start()

                p8 = threading.Thread(target=containerWatch, args=(c_8,))
                p8.start()

                #monitor the services of the appliance.
                services = threading.Thread(target=connectorApplianceServices, args=())
                services.start()

                #keep our main process alive and responsive.
                while threading.active_count() > 0:
                        time.sleep(1)
except:
    epoch = time.time()
    stamp = datetime.datetime.fromtimestamp(epoch).strftime('%c')
    logging.exception(str(stamp))
    sys.exit(1)
