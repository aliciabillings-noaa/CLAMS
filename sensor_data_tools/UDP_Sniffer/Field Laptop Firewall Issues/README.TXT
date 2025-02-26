
AFSC "Field Laptops" have an OS policy that forces all non-domain
network cnnections to be assigned the "Public" profile. They also
have a policy where firewall exceptions for "Public" connections
are ignored. The result of this is that even with local admin privs
users cannot add firewall exceptions for applications or data from
network based sensors. That's a big problem.

When run as an administrator, the script "change_eth_profile.ps1" 
will change your network interface from "Public" to "Private". It
will not change the profile if it is already set to Private or
DomainAuthenticated.

Again, using the local admin account, you can then add firewall
exceptions to allow an application thru the firewall or to allow
broadcast sensor data in thru the firewall. The latter is required
for receiving SCS data on the Dyson.

On the Dyson, SCS data is transmitted as UDP on ports 45000-45020.
You will need to make an incoming exception for UDP traffic to ports
in that range.

You can automate the running of this script using the 
"Change_Ethernet_profile_on_connect_task_2024.xml" task scheduler
task. You will need to edit the path to the script on line 43
based on where you have copied the change_eth_profile.ps1 script.

Log in as local admin and run task scheduler. Import the task.
Close task sceduler. Reboot. Check if the interface is Private.