namespace py _saas 

struct Ip {
	1: i64 ipv4						,
	2: i64 ipv4_netmask				,
}


struct Vps {
   1 : i64 id                       ,
   2 : list<Ip> ext_ips           	,
   3 : Ip gateway      				,
   4 : string password              ,
   5 : i32 os                    ,                       // os类型
   6 : map<i32, i32> harddisks      ,                       //
   7 : i64 ram                      ,                       //单位M
   8 : i16 cpu                      ,                       //几个core
   9 : i64 host_id                  ,                       //如pc1.42qu.us
  10 : i16 state                    ,
  11 : optional Ip int_ip           ,                       //内网IP
  12 : optional i64 bandwidth       ,                       //带宽 单位 Mbps, 0 或 None 表示不限制
  13 : optional i32 qos             ,                       //带宽优先级 0 为默认值 , 1 为高优先级
  14 : optional string template_image		,
}

struct NetFlow {
	1: i64 vps_id					,
	2: i64 rx						,
	3: i64 tx						,
}

enum Cmd{
  NONE        = 0,
  OPEN        = 1,
  CLOSE       = 2,
  REBOOT      = 3,
  RM          = 4,
  BANDWIDTH   = 5, //调整带宽
  OS          = 6, //更换操作系统
  UPGRADE     = 7,
}


typedef i64 VpsId 
typedef i64 Id

service VPS {

   Id    todo            ( 1:i64  host_id , 2:Cmd cmd),
   void  done            ( 1:i64  host_id , 2:Cmd cmd, 3:Id id, 4:i32 state=0, 5:string message=''), 

   Vps   vps             ( 1:i64 vps_id   ),
   void  netflow_save    ( 1:i64 host_id, 2:list<NetFlow> netflow, 3:i64 timestamp),

   void  plot            ( 1:i64 cid, 2:i64 rid, 3:i64 value ),

   string   sms          ( 1:list<string>  number_list, 2:string txt),
   void  host_refresh    ( 1:i64 host_id , 2:i16 hd_remain, 3:i64 ram_remain, 4:i16 hd_total=0, 5:i64 ram_total=0),
}



