import _env

def vps_open(vps):
    print vps

if '__main__' == __name__:
    from saas.ttypes import Vps
    vps = Vps(ipv4_gateway=2013143905, ram=2048, cpu=1, ipv4_netmask=4294967280, host_id=2, password='k5chpa2n4mz2', os=10002, id=28, hd=50, ipv4=2013143908)    
    vps_open(vps)
