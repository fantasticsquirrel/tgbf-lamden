You can mint or list Lamden Name Service (LNS) namespaces. Namespaces will be used as aliases for Lamden addresses so that you can in future send TAU or tokens to a namespace instead of addresses.  

If you own a namespace then it's connected to your Lamden address and automatically resolves to that address.  

Minting namespace:  
`/{{handle}} mint <namespace>`  

Example for minting `test`:  
`/{{handle}} mint test`  

Transfer namespace to another address:  
`/{{handle}} transfer <namespace> <to address>`  

Example for transfering namespace `test` to normal address:  
`/{{handle}} transfer test ae7d14d6d9b8443f881ba6244727b69b681010e782d4fe482dbfb0b6aca02d5d`  

Example for sending namespace `test` to namespace `endogen`:  
`/{{handle}} transfer test endogen`  

Resolving namespace to address:  
`/{{handle}} resolve <namespace>`  

Example for resolving namespace `endogen` to address:  
`/{{handle}} resolve endogen`  

List namespaces connected to your bot wallet:  
`/{{handle}} list`  

Show number of minted namespaces:  
`/{{handle}} count`  
