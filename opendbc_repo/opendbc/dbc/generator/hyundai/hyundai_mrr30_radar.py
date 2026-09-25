from io import StringIO


def generate() -> dict[str, str]:
  f = StringIO()
  f.write("""
VERSION ""


NS_ :
  NS_DESC_
  CM_
  BA_DEF_
  BA_
  VAL_
  CAT_DEF_
  CAT_
  FILTER
  BA_DEF_DEF_
  EV_DATA_
  ENVVAR_DATA_
  SGTYPE_
  SGTYPE_VAL_
  BA_DEF_SGTYPE_
  BA_SGTYPE_
  SIG_TYPE_REF_
  VAL_TABLE_
  SIG_GROUP_
  SIG_VALTYPE_
  SIGTYPE_VALTYPE_
  BO_TX_BU_
  BA_DEF_REL_
  BA_REL_
  BA_DEF_DEF_REL_
  BU_SG_REL_
  BU_EV_REL_
  BU_BO_REL_
  SG_MUL_VAL_

BS_:

BU_: XXX
""")

  for a in range(0x210, 0x210 + 16):
    f.write(f"""
BO_ {a} RADAR_TRACK_{a:x}: 32 RADAR
 SG_ CHECKSUM : 0|16@1+ (1,0) [0|65535] "" XXX
 SG_ COUNTER : 16|8@1+ (1,0) [0|255] "" XXX
 SG_ 1_COUNTER_255 : 47|8@0+ (1,0) [0|255] "" XXX
 SG_ 1_STATE_ALT : 51|4@0+ (1,0) [0|15] "" XXX
 SG_ 1_STATE : 55|4@0+ (1,0) [0|15] "" XXX
 SG_ 1_NEW_SIGNAL_3 : 63|8@0- (1,0) [0|255] "" XXX
 SG_ 1_LONG_DIST : 64|12@1+ (0.05,0) [0|4095] "" XXX
 SG_ 1_LAT_DIST : 76|12@1- (0.05,0) [0|4095] "" XXX
 SG_ 1_REL_SPEED : 88|14@1- (0.01,0) [0|16383] "" XXX
 SG_ 1_NEW_SIGNAL_1 : 102|2@1+ (1,0) [0|3] "" XXX
 SG_ 1_LAT_ACCEL : 104|13@1- (1,0) [0|8191] "" XXX
 SG_ 1_REL_ACCEL : 118|10@1- (1,0) [0|1023] "" XXX
 SG_ 2_COUNTER_255 : 175|8@0+ (1,0) [0|255] "" XXX
 SG_ 2_STATE_ALT : 179|4@0+ (1,0) [0|15] "" XXX
 SG_ 2_STATE : 183|4@0+ (1,0) [0|15] "" XXX
 SG_ 2_NEW_SIGNAL_3 : 191|8@0- (1,0) [0|255] "" XXX
 SG_ 2_LONG_DIST : 192|12@1+ (0.05,0) [0|4095] "" XXX
 SG_ 2_LAT_DIST : 204|12@1- (0.05,0) [0|4095] "" XXX
 SG_ 2_REL_SPEED : 216|14@1- (0.01,0) [0|65535] "" XXX
 SG_ 2_NEW_SIGNAL_1 : 230|2@1+ (1,0) [0|3] "" XXX
 SG_ 2_LAT_ACCEL : 232|13@1- (1,0) [0|8191] "" XXX
 SG_ 2_REL_ACCEL : 246|10@1- (1,0) [0|1023] "" XXX
""")
  return {"hyundai_mrr30_radar.dbc": f.getvalue()}
