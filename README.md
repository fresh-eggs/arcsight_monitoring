# arcsight_monitoring
Are you looking for an easy way to monitor your Arcsight Connectors with the help of Zabbix? Then feel free to keep reading.


## WHAT IS THIS
A somewhat exhaustive monitoring solution for an Arcsight Connector Appliance with the help of zabbix discovery rules and python.
RHEL 6.6+ tested.


## THE PIECES
The first is essentially a custom zabbix agent written from scratch in python. It is a multithreaded application designed to 
provide an Arcsight Administrator an easy, self healing way to instantly begin monitoring their connector appliances with zabbix.

The bot is self healing in the sense that the Zabbix template makes heavy use of custom discovery rules, allowing for the
connector agents details to be reflected in Zabbix automatically.

Second is the aforementioned zabbix template. The template has a few static items, as well as a bunch of prototypes. The idea is that 
everytime the bot is run, it will use the discovery items to update the entry on the zabbix server about what destinations and agents 
are running on each container.


## HOW TO SETUP
* Import the provided template into your zabbix server

* Create an entry for the connector you want to monitor. Ensure that the name in zabbix is an exact match of the short form hostname for your connector (ex: fqx2s3.example.pizza.ca = fqx2s3). Apply the Connector template to this entry. 

* On your connector appliance, create a /home/scripts/zabbix_bot/ directory. 

* Push the connector_bot.py and start_bot.sh wrapper into the directory we just created. Ensure start_bot.sh is executable.

* Finaly, with the zabbix entry in place and the scripts on the box, simply start up the bot on the appliance by calling ./start_bot.sh

The script will begin with reading the agent.properties file and go on creating item/trigger prototypes based on the destination and 
agent information it finds in the agent.properties file.

If ever a change is made to the agent, i.e. a destination is added or removed, there is no need to manually update the host in zabbix.
Simply restart the bot on the appliance and it will re-read the agent.protperties file, automatically updating the host entry in zabbix.
