namespace py saas 

typedef i64 Ip 


struct Vps {
   1 : i64 id                        ,
   2 : optional Ip ipv4              ,
   3 : optional Ip ipv4_netmask      ,
   4 : optional Ip ipv4_gateway      ,
   5 : string password               ,
   6 : i64 os                        ,                       //os的id会软连接到真实的os镜像
   7 : i16 hd                        ,                       //单位G
   8 : i64 ram                       ,                       //单位M
   9 : i16 cpu                       ,                       //几个core
  10 : i64 host_id                   ,                       //如pc1.42qu.us
}

enum Cmd{
  NONE    = 0,
  OPEN    = 1,
  CLOSE   = 2,
  RESTART = 3,
}

struct Task {
    1:          Cmd   cmd = 0,
    2: optional i64   id
}

typedef i64 VpsId 

service VPS {

   Task  todo            ( 1:i64  host_id  ),
   void  done            ( 1:i64  host_id , 2:Task todo , 3:i32 state=0, 4:string message=''), 

   Vps   vps             ( 1:i64  vps_id   ),
   void  netflow_save    ( 1:map<VpsId, list<i64>> netflow),
}



