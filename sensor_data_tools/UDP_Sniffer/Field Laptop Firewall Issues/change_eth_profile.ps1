<#

AFSC "Field Laptops" have an OS policy that forces all non-domain
network cnnections to be assigned the "Public" profile. They also
have a policy where firewall exceptions for "Public" connections
are ignored. The result of this is that even with local admin privs
users cannot add firewall exceptions for applications or data from
network based sensors. That's a big problem.

This script will change the built in Ethernet interface(s) profile
from the default "Public" profile to "Private". This must be executed
from an elevated powershell prompt. This script will not change the
profile if it is already set to Private or DomainAuthenticated.

This can also be used with the task scheduler task distributed with
this script. That task is triggered when an Ethernet interface is
activated and should automagically keep your interface set to the
Private profile, allowing your firewall exceptions to work and your
data to flow in.


You can test if this is successful by running this command from an
elevated powershell prompt, replacing <interface name> with the name
of the network interface:

PS >(Get-NetConnectionProfile -InterfaceAlias <interface name>).NetworkCategory

If successful that command should return "Private"

Example:

PS C:\windows\system32> (Get-NetConnectionProfile -InterfaceAlias 'Ethernet').NetworkCategory
Private

#>


#  get the Ethernet interfaces.
$interfaceNameArray = (Get-NetAdapter -Name Eth* | select Name).Name

#  for each interface, check if it is public and change to private, if necessary.
foreach ($interface in $interfaceNameArray)
{
    #  try to get the profile object
    Write-Output "Trying $interface..."
    try
    {
        $profileObj = Get-NetConnectionProfile -InterfaceAlias $interface -ErrorAction stop
    }
    catch
    {
        #  object doesn't exist when the interface is not connected
        Write-Output "$interface is not connected."
    }


    #  if there is a profile object, check what profile it is using and change if public
    if ($profileObj)
    {
        $currentProfile = $profileObj.NetworkCategory.ToString()
        if ($currentProfile.ToLower() -eq 'public')
        {
            Set-NetConnectionProfile -InterfaceAlias $interface -NetworkCategory 'Private'
            $newNetName = (Get-NetConnectionProfile -InterfaceAlias $interface).NetworkCategory.ToString()
            Write-Output "Changed $interface from the Public network profile to $newNetName."
        }
        elseif ($currentProfile.ToLower() -eq 'private')
        {
            Write-Output "$interface is already using the Private profile."
        }
        else 
        {
            #  we're going to assume this is DomainAuthenticated but maybe there are othrs?
            Write-Output "$interface is using the DomainAuthenticated profile and will not be changed."
        }
    }
}
