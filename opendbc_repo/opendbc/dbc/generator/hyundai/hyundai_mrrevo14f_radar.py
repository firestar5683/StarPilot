#!/usr/bin/env python3
import os

if __name__ == "__main__":
  dbc_name = os.path.basename(__file__).replace(".py", ".dbc")
  hyundai_path = os.path.dirname(os.path.realpath(__file__))
  with open(os.path.join(hyundai_path, dbc_name), "w", encoding="utf-8") as f:
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

BO_ 1537 RADAR_LEAD: 8 RADAR
 SG_ DISTANCE : 0|10@1+ (0.25,0) [0|255.75] "" XXX
 SG_ LATERAL : 10|11@1+ (0.03,-30.705) [-30.705|30.705] "" XXX
 SG_ SPEED : 21|10@1+ (0.25,-128) [-128|127.75] "" XXX
 SG_ ID : 31|9@1+ (1,0) [0|511] "" XXX
 SG_ SOMETHING_1 : 42|8@1+ (1,-128) [-128|127] "" XXX
 SG_ SOMETHING_2 : 50|6@1+ (1,-32) [-32|31] "" XXX
 SG_ COUNTER : 56|4@1+ (1,0) [0|15] "" XXX
 SG_ CHECKSUM : 63|4@0+ (1,0) [0|15] "" XXX
""")

    for a in range(0x602, 0x602 + 16):
      f.write(f"""
BO_ {a} RADAR_TRACK_{a:x}: 8 RADAR
 SG_ 1_DISTANCE : 0|10@1+ (0.25,0) [0|255.75] "" XXX
 SG_ 1_LATERAL : 10|11@1+ (0.03,-30.705) [-30.705|30.705] "" XXX
 SG_ 1_SPEED : 21|10@1+ (0.25,-128) [-128|127.75] "" XXX
 SG_ 2_DISTANCE : 31|10@1+ (0.25,0) [0|255.75] "" XXX
 SG_ 2_LATERAL : 41|11@1+ (0.03,-30.705) [-30.705|30.705] "" XXX
 SG_ 2_SPEED : 52|10@1+ (0.25,-128) [-128|127.75] "" XXX
 SG_ COUNTER : 62|2@1+ (1,0) [0|3] "" XXX
""")

    for a in range(0x612, 0x612 + 6):
      f.write(f"""
BO_ {a} RADAR_ALT_{a:x}: 8 RADAR
 SG_ DISTANCE : 0|10@1+ (0.25,0) [0|255.75] "" XXX
 SG_ LATERAL : 10|11@1+ (0.03,-30.705) [-30.705|30.705] "" XXX
 SG_ SPEED : 21|10@1+ (0.25,-128) [-128|127.75] "" XXX
 SG_ ID : 31|9@1+ (1,0) [0|511] "" XXX
 SG_ SOMETHING_1 : 42|8@1+ (1,-128) [-128|127] "" XXX
 SG_ SOMETHING_2 : 50|6@1+ (1,-32) [-32|31] "" XXX
 SG_ COUNTER : 56|4@1+ (1,0) [0|15] "" XXX
 SG_ CHECKSUM : 63|4@0+ (1,0) [0|15] "" XXX
""")
