# To build the docker image:
sudo docker build -t lcalzado/vpn_monitor .

# To run the container:
sudo docker run -p 5000:5000 -e TZ=$(cat /etc/timezone) -e FORTIPASS='I3.14team' -e FORTIUSER='nati' -e FORTIIP='172.16.143.175' -e DEVTYPE='fortinet' -d lcalzado/vpn_monitor
