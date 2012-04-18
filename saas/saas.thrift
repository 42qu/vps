namespace py saas 

typedef i32 Ip 


struct Vps {
   0 : i32 host_id                   ,                       //如pc1.42qu.us
   1 : i32 id                        ,
   2 : optional Ip ipv4              ,
   3 : optional Ip ipv4_netmask      ,
   4 : optional Ip ipv4_gateway      ,
   5 : string password               ,
   6 : i32 os                        ,                       //os的id会软连接到真实的os镜像
   7 : i16 hd                        ,                       //单位G
   8 : i32 ram                       ,                       //单位M
   9 : i16 cpu                       ,                       //几个core
}

enum Action{
  NONE    = 0,
  OPEN    = 1,
  CLOSE   = 2,
  RESTART = 3,
}

struct Todo {
    0: Action action,
    1: i32    id
}

service VPS {


   Todo  to_do       ( 1:i32 host_id  ),

   Vps  info         ( 1:i32 vps_id ),
 
   void opened       ( 1:i32 vps_id ),
   void closed       ( 1:i32 vps_id ),
   void restart      ( 1:i32 vps_id ),


}


