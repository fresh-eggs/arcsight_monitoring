# arcsight_monitoring
Are you looking for an easy way to monitor your Arcsight Connectors with the help of Zabbix? Then feel free to keep reading.


## WHAT IS THIS
A somewhat exhaustive monitoring solution for an Arcsight Connector Appliance with the help of zabbix discovery rules and python.
RHEL 6.6+ tested.


## THE PIECES
### arcsight_connector_template.xml
This is the template you should be importing into Zabbix. It houses multiple applications, items, triggers and twp important discovery rule trappers.

The discovery rule trappers are the bulk of what make this solution useful. The connector_appliance_bot will use these rules to update the entry for a connector on the zabbix server when it notices changes in the agent properties file.



### connector_appliance_bot.py
This boils down to a custom zabbix agent written from scratch in python. It is a multithreaded application that makes heavy use of the zabbix_sender binary. It is designed to provide an Arcsight Administrator with a monitoring solution that comes with little to no overhead.

At every startup, the bot will first, inspect the agent.properties file and determine if there is an agent configured on a container or not. IF it determines there is none the c_x.state item will reflect EMPTY as a state.

However, if it determines that there is an agent configured, the bot will continue by programatically determining the number of agents and their detiantions, followed by crafting a JSON request with that information in order to send out to our custom discovery rule.



### start_bot.sh
Used as a simple wrapper allowing us to hook the connector bot onto the init process. Effectively keeping it alive if you start it over an SSH session.


## HOW TO SETUP
* Import the provided template into your zabbix server

* Create an entry for the connector you want to monitor. Ensure that the name in zabbix is an exact match of the short form hostname for your connector (ex: fqx2s3.example.pizza.ca = fqx2s3). Apply the Connector template to this entry. 

* On your connector appliance, create a /home/scripts/zabbix_bot/ directory. 

* Push the connector_bot.py and start_bot.sh wrapper into the directory we just created. Ensure start_bot.sh is executable.

* Change the zabbix server IP global variable in the script to point towards your server. (cmd line arguments to come...)

* Ensure that the [hp-health RPM](https://downloads.linux.hpe.com/SDR/repo/mcp/centos/6/i386/10.00/) is installed on your appliance. 

* Finaly, with the zabbix entry in place and the scripts on the box, simply start up the bot on the appliance by calling ./start_bot.sh

The script will begin with reading the agent.properties file and go on creating item/trigger prototypes based on the destination and 
agent information it finds in the agent.properties file.

If ever a change is made to the agent, i.e. a destination is added or removed, there is no need to manually update the host in zabbix.
Simply restart the bot on the appliance and it will re-read the agent.protperties file, automatically updating the host entry in zabbix.
