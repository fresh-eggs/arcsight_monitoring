# arcsight_monitoring
Zabbix templates and custom python agents designed to monitor Arcsight connectors.

This repository consists of two major components. 

WHAT IS THIS
A somewhat exhaustive monitoring solution for an Arcsight Connector Appliance with the help of zabbix, python and discovery rules.
RHEL 6.6+ tested.

\n

THE PIECES
The first is essentially a custom zabbix agent written from scratch in python. It is a multithreaded application designed to 
provide an Arcsight Administrator an easy, self healing way to instantly begin monitoring their connector appliances with zabbix.

The bot is self healing in the sense that the Zabbix template makes heavy use of custom discovery rules, allowing for the
connector agents details to be reflected in Zabbix automatically.

Second is the aforementioned zabbix template. The template has a few static items, as well as a bunch of prototypes. The idea is that 
everytime the bot is run, it will use the discovery items to update the entry on the zabbix server about what destinations and agents 
are running on each container.





HOW TO SETUP
First step required is to import the connector template into zabbix. The connector template is designed to have the Zabbix agent
template be linked to it.

Once imported, you should create an entry for you connector appliance. The name of the entry in zabbix should match EXACTLY 
the short form host name that the box has (ex: fqx2s3.example.pizza.ca = fqx2s3).

After the entry is created and the connector template applied to it, you should push the script and wrapper to your arcsight connector.

Finaly, with the zabbix entry in place and the scripts on the box, simply start up the bot on the appliance by calling ./start_bot.sh

The script will begin with reading the agent.properties file and go on creating item/trigger prototypes based on the destination and 
agent information it finds in the agent.properties file.

If ever a change is made to the agent, i.e. a destination is added or removed, there is no need to manually update the host in zabbix.
Simply restart the bot on the appliance and it will re-read the agent.protperties file, automatically updating the host entry in zabbix.
