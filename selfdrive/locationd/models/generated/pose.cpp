#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_4038237010904669995) {
   out_4038237010904669995[0] = delta_x[0] + nom_x[0];
   out_4038237010904669995[1] = delta_x[1] + nom_x[1];
   out_4038237010904669995[2] = delta_x[2] + nom_x[2];
   out_4038237010904669995[3] = delta_x[3] + nom_x[3];
   out_4038237010904669995[4] = delta_x[4] + nom_x[4];
   out_4038237010904669995[5] = delta_x[5] + nom_x[5];
   out_4038237010904669995[6] = delta_x[6] + nom_x[6];
   out_4038237010904669995[7] = delta_x[7] + nom_x[7];
   out_4038237010904669995[8] = delta_x[8] + nom_x[8];
   out_4038237010904669995[9] = delta_x[9] + nom_x[9];
   out_4038237010904669995[10] = delta_x[10] + nom_x[10];
   out_4038237010904669995[11] = delta_x[11] + nom_x[11];
   out_4038237010904669995[12] = delta_x[12] + nom_x[12];
   out_4038237010904669995[13] = delta_x[13] + nom_x[13];
   out_4038237010904669995[14] = delta_x[14] + nom_x[14];
   out_4038237010904669995[15] = delta_x[15] + nom_x[15];
   out_4038237010904669995[16] = delta_x[16] + nom_x[16];
   out_4038237010904669995[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2572217743337337909) {
   out_2572217743337337909[0] = -nom_x[0] + true_x[0];
   out_2572217743337337909[1] = -nom_x[1] + true_x[1];
   out_2572217743337337909[2] = -nom_x[2] + true_x[2];
   out_2572217743337337909[3] = -nom_x[3] + true_x[3];
   out_2572217743337337909[4] = -nom_x[4] + true_x[4];
   out_2572217743337337909[5] = -nom_x[5] + true_x[5];
   out_2572217743337337909[6] = -nom_x[6] + true_x[6];
   out_2572217743337337909[7] = -nom_x[7] + true_x[7];
   out_2572217743337337909[8] = -nom_x[8] + true_x[8];
   out_2572217743337337909[9] = -nom_x[9] + true_x[9];
   out_2572217743337337909[10] = -nom_x[10] + true_x[10];
   out_2572217743337337909[11] = -nom_x[11] + true_x[11];
   out_2572217743337337909[12] = -nom_x[12] + true_x[12];
   out_2572217743337337909[13] = -nom_x[13] + true_x[13];
   out_2572217743337337909[14] = -nom_x[14] + true_x[14];
   out_2572217743337337909[15] = -nom_x[15] + true_x[15];
   out_2572217743337337909[16] = -nom_x[16] + true_x[16];
   out_2572217743337337909[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_362240871876916223) {
   out_362240871876916223[0] = 1.0;
   out_362240871876916223[1] = 0.0;
   out_362240871876916223[2] = 0.0;
   out_362240871876916223[3] = 0.0;
   out_362240871876916223[4] = 0.0;
   out_362240871876916223[5] = 0.0;
   out_362240871876916223[6] = 0.0;
   out_362240871876916223[7] = 0.0;
   out_362240871876916223[8] = 0.0;
   out_362240871876916223[9] = 0.0;
   out_362240871876916223[10] = 0.0;
   out_362240871876916223[11] = 0.0;
   out_362240871876916223[12] = 0.0;
   out_362240871876916223[13] = 0.0;
   out_362240871876916223[14] = 0.0;
   out_362240871876916223[15] = 0.0;
   out_362240871876916223[16] = 0.0;
   out_362240871876916223[17] = 0.0;
   out_362240871876916223[18] = 0.0;
   out_362240871876916223[19] = 1.0;
   out_362240871876916223[20] = 0.0;
   out_362240871876916223[21] = 0.0;
   out_362240871876916223[22] = 0.0;
   out_362240871876916223[23] = 0.0;
   out_362240871876916223[24] = 0.0;
   out_362240871876916223[25] = 0.0;
   out_362240871876916223[26] = 0.0;
   out_362240871876916223[27] = 0.0;
   out_362240871876916223[28] = 0.0;
   out_362240871876916223[29] = 0.0;
   out_362240871876916223[30] = 0.0;
   out_362240871876916223[31] = 0.0;
   out_362240871876916223[32] = 0.0;
   out_362240871876916223[33] = 0.0;
   out_362240871876916223[34] = 0.0;
   out_362240871876916223[35] = 0.0;
   out_362240871876916223[36] = 0.0;
   out_362240871876916223[37] = 0.0;
   out_362240871876916223[38] = 1.0;
   out_362240871876916223[39] = 0.0;
   out_362240871876916223[40] = 0.0;
   out_362240871876916223[41] = 0.0;
   out_362240871876916223[42] = 0.0;
   out_362240871876916223[43] = 0.0;
   out_362240871876916223[44] = 0.0;
   out_362240871876916223[45] = 0.0;
   out_362240871876916223[46] = 0.0;
   out_362240871876916223[47] = 0.0;
   out_362240871876916223[48] = 0.0;
   out_362240871876916223[49] = 0.0;
   out_362240871876916223[50] = 0.0;
   out_362240871876916223[51] = 0.0;
   out_362240871876916223[52] = 0.0;
   out_362240871876916223[53] = 0.0;
   out_362240871876916223[54] = 0.0;
   out_362240871876916223[55] = 0.0;
   out_362240871876916223[56] = 0.0;
   out_362240871876916223[57] = 1.0;
   out_362240871876916223[58] = 0.0;
   out_362240871876916223[59] = 0.0;
   out_362240871876916223[60] = 0.0;
   out_362240871876916223[61] = 0.0;
   out_362240871876916223[62] = 0.0;
   out_362240871876916223[63] = 0.0;
   out_362240871876916223[64] = 0.0;
   out_362240871876916223[65] = 0.0;
   out_362240871876916223[66] = 0.0;
   out_362240871876916223[67] = 0.0;
   out_362240871876916223[68] = 0.0;
   out_362240871876916223[69] = 0.0;
   out_362240871876916223[70] = 0.0;
   out_362240871876916223[71] = 0.0;
   out_362240871876916223[72] = 0.0;
   out_362240871876916223[73] = 0.0;
   out_362240871876916223[74] = 0.0;
   out_362240871876916223[75] = 0.0;
   out_362240871876916223[76] = 1.0;
   out_362240871876916223[77] = 0.0;
   out_362240871876916223[78] = 0.0;
   out_362240871876916223[79] = 0.0;
   out_362240871876916223[80] = 0.0;
   out_362240871876916223[81] = 0.0;
   out_362240871876916223[82] = 0.0;
   out_362240871876916223[83] = 0.0;
   out_362240871876916223[84] = 0.0;
   out_362240871876916223[85] = 0.0;
   out_362240871876916223[86] = 0.0;
   out_362240871876916223[87] = 0.0;
   out_362240871876916223[88] = 0.0;
   out_362240871876916223[89] = 0.0;
   out_362240871876916223[90] = 0.0;
   out_362240871876916223[91] = 0.0;
   out_362240871876916223[92] = 0.0;
   out_362240871876916223[93] = 0.0;
   out_362240871876916223[94] = 0.0;
   out_362240871876916223[95] = 1.0;
   out_362240871876916223[96] = 0.0;
   out_362240871876916223[97] = 0.0;
   out_362240871876916223[98] = 0.0;
   out_362240871876916223[99] = 0.0;
   out_362240871876916223[100] = 0.0;
   out_362240871876916223[101] = 0.0;
   out_362240871876916223[102] = 0.0;
   out_362240871876916223[103] = 0.0;
   out_362240871876916223[104] = 0.0;
   out_362240871876916223[105] = 0.0;
   out_362240871876916223[106] = 0.0;
   out_362240871876916223[107] = 0.0;
   out_362240871876916223[108] = 0.0;
   out_362240871876916223[109] = 0.0;
   out_362240871876916223[110] = 0.0;
   out_362240871876916223[111] = 0.0;
   out_362240871876916223[112] = 0.0;
   out_362240871876916223[113] = 0.0;
   out_362240871876916223[114] = 1.0;
   out_362240871876916223[115] = 0.0;
   out_362240871876916223[116] = 0.0;
   out_362240871876916223[117] = 0.0;
   out_362240871876916223[118] = 0.0;
   out_362240871876916223[119] = 0.0;
   out_362240871876916223[120] = 0.0;
   out_362240871876916223[121] = 0.0;
   out_362240871876916223[122] = 0.0;
   out_362240871876916223[123] = 0.0;
   out_362240871876916223[124] = 0.0;
   out_362240871876916223[125] = 0.0;
   out_362240871876916223[126] = 0.0;
   out_362240871876916223[127] = 0.0;
   out_362240871876916223[128] = 0.0;
   out_362240871876916223[129] = 0.0;
   out_362240871876916223[130] = 0.0;
   out_362240871876916223[131] = 0.0;
   out_362240871876916223[132] = 0.0;
   out_362240871876916223[133] = 1.0;
   out_362240871876916223[134] = 0.0;
   out_362240871876916223[135] = 0.0;
   out_362240871876916223[136] = 0.0;
   out_362240871876916223[137] = 0.0;
   out_362240871876916223[138] = 0.0;
   out_362240871876916223[139] = 0.0;
   out_362240871876916223[140] = 0.0;
   out_362240871876916223[141] = 0.0;
   out_362240871876916223[142] = 0.0;
   out_362240871876916223[143] = 0.0;
   out_362240871876916223[144] = 0.0;
   out_362240871876916223[145] = 0.0;
   out_362240871876916223[146] = 0.0;
   out_362240871876916223[147] = 0.0;
   out_362240871876916223[148] = 0.0;
   out_362240871876916223[149] = 0.0;
   out_362240871876916223[150] = 0.0;
   out_362240871876916223[151] = 0.0;
   out_362240871876916223[152] = 1.0;
   out_362240871876916223[153] = 0.0;
   out_362240871876916223[154] = 0.0;
   out_362240871876916223[155] = 0.0;
   out_362240871876916223[156] = 0.0;
   out_362240871876916223[157] = 0.0;
   out_362240871876916223[158] = 0.0;
   out_362240871876916223[159] = 0.0;
   out_362240871876916223[160] = 0.0;
   out_362240871876916223[161] = 0.0;
   out_362240871876916223[162] = 0.0;
   out_362240871876916223[163] = 0.0;
   out_362240871876916223[164] = 0.0;
   out_362240871876916223[165] = 0.0;
   out_362240871876916223[166] = 0.0;
   out_362240871876916223[167] = 0.0;
   out_362240871876916223[168] = 0.0;
   out_362240871876916223[169] = 0.0;
   out_362240871876916223[170] = 0.0;
   out_362240871876916223[171] = 1.0;
   out_362240871876916223[172] = 0.0;
   out_362240871876916223[173] = 0.0;
   out_362240871876916223[174] = 0.0;
   out_362240871876916223[175] = 0.0;
   out_362240871876916223[176] = 0.0;
   out_362240871876916223[177] = 0.0;
   out_362240871876916223[178] = 0.0;
   out_362240871876916223[179] = 0.0;
   out_362240871876916223[180] = 0.0;
   out_362240871876916223[181] = 0.0;
   out_362240871876916223[182] = 0.0;
   out_362240871876916223[183] = 0.0;
   out_362240871876916223[184] = 0.0;
   out_362240871876916223[185] = 0.0;
   out_362240871876916223[186] = 0.0;
   out_362240871876916223[187] = 0.0;
   out_362240871876916223[188] = 0.0;
   out_362240871876916223[189] = 0.0;
   out_362240871876916223[190] = 1.0;
   out_362240871876916223[191] = 0.0;
   out_362240871876916223[192] = 0.0;
   out_362240871876916223[193] = 0.0;
   out_362240871876916223[194] = 0.0;
   out_362240871876916223[195] = 0.0;
   out_362240871876916223[196] = 0.0;
   out_362240871876916223[197] = 0.0;
   out_362240871876916223[198] = 0.0;
   out_362240871876916223[199] = 0.0;
   out_362240871876916223[200] = 0.0;
   out_362240871876916223[201] = 0.0;
   out_362240871876916223[202] = 0.0;
   out_362240871876916223[203] = 0.0;
   out_362240871876916223[204] = 0.0;
   out_362240871876916223[205] = 0.0;
   out_362240871876916223[206] = 0.0;
   out_362240871876916223[207] = 0.0;
   out_362240871876916223[208] = 0.0;
   out_362240871876916223[209] = 1.0;
   out_362240871876916223[210] = 0.0;
   out_362240871876916223[211] = 0.0;
   out_362240871876916223[212] = 0.0;
   out_362240871876916223[213] = 0.0;
   out_362240871876916223[214] = 0.0;
   out_362240871876916223[215] = 0.0;
   out_362240871876916223[216] = 0.0;
   out_362240871876916223[217] = 0.0;
   out_362240871876916223[218] = 0.0;
   out_362240871876916223[219] = 0.0;
   out_362240871876916223[220] = 0.0;
   out_362240871876916223[221] = 0.0;
   out_362240871876916223[222] = 0.0;
   out_362240871876916223[223] = 0.0;
   out_362240871876916223[224] = 0.0;
   out_362240871876916223[225] = 0.0;
   out_362240871876916223[226] = 0.0;
   out_362240871876916223[227] = 0.0;
   out_362240871876916223[228] = 1.0;
   out_362240871876916223[229] = 0.0;
   out_362240871876916223[230] = 0.0;
   out_362240871876916223[231] = 0.0;
   out_362240871876916223[232] = 0.0;
   out_362240871876916223[233] = 0.0;
   out_362240871876916223[234] = 0.0;
   out_362240871876916223[235] = 0.0;
   out_362240871876916223[236] = 0.0;
   out_362240871876916223[237] = 0.0;
   out_362240871876916223[238] = 0.0;
   out_362240871876916223[239] = 0.0;
   out_362240871876916223[240] = 0.0;
   out_362240871876916223[241] = 0.0;
   out_362240871876916223[242] = 0.0;
   out_362240871876916223[243] = 0.0;
   out_362240871876916223[244] = 0.0;
   out_362240871876916223[245] = 0.0;
   out_362240871876916223[246] = 0.0;
   out_362240871876916223[247] = 1.0;
   out_362240871876916223[248] = 0.0;
   out_362240871876916223[249] = 0.0;
   out_362240871876916223[250] = 0.0;
   out_362240871876916223[251] = 0.0;
   out_362240871876916223[252] = 0.0;
   out_362240871876916223[253] = 0.0;
   out_362240871876916223[254] = 0.0;
   out_362240871876916223[255] = 0.0;
   out_362240871876916223[256] = 0.0;
   out_362240871876916223[257] = 0.0;
   out_362240871876916223[258] = 0.0;
   out_362240871876916223[259] = 0.0;
   out_362240871876916223[260] = 0.0;
   out_362240871876916223[261] = 0.0;
   out_362240871876916223[262] = 0.0;
   out_362240871876916223[263] = 0.0;
   out_362240871876916223[264] = 0.0;
   out_362240871876916223[265] = 0.0;
   out_362240871876916223[266] = 1.0;
   out_362240871876916223[267] = 0.0;
   out_362240871876916223[268] = 0.0;
   out_362240871876916223[269] = 0.0;
   out_362240871876916223[270] = 0.0;
   out_362240871876916223[271] = 0.0;
   out_362240871876916223[272] = 0.0;
   out_362240871876916223[273] = 0.0;
   out_362240871876916223[274] = 0.0;
   out_362240871876916223[275] = 0.0;
   out_362240871876916223[276] = 0.0;
   out_362240871876916223[277] = 0.0;
   out_362240871876916223[278] = 0.0;
   out_362240871876916223[279] = 0.0;
   out_362240871876916223[280] = 0.0;
   out_362240871876916223[281] = 0.0;
   out_362240871876916223[282] = 0.0;
   out_362240871876916223[283] = 0.0;
   out_362240871876916223[284] = 0.0;
   out_362240871876916223[285] = 1.0;
   out_362240871876916223[286] = 0.0;
   out_362240871876916223[287] = 0.0;
   out_362240871876916223[288] = 0.0;
   out_362240871876916223[289] = 0.0;
   out_362240871876916223[290] = 0.0;
   out_362240871876916223[291] = 0.0;
   out_362240871876916223[292] = 0.0;
   out_362240871876916223[293] = 0.0;
   out_362240871876916223[294] = 0.0;
   out_362240871876916223[295] = 0.0;
   out_362240871876916223[296] = 0.0;
   out_362240871876916223[297] = 0.0;
   out_362240871876916223[298] = 0.0;
   out_362240871876916223[299] = 0.0;
   out_362240871876916223[300] = 0.0;
   out_362240871876916223[301] = 0.0;
   out_362240871876916223[302] = 0.0;
   out_362240871876916223[303] = 0.0;
   out_362240871876916223[304] = 1.0;
   out_362240871876916223[305] = 0.0;
   out_362240871876916223[306] = 0.0;
   out_362240871876916223[307] = 0.0;
   out_362240871876916223[308] = 0.0;
   out_362240871876916223[309] = 0.0;
   out_362240871876916223[310] = 0.0;
   out_362240871876916223[311] = 0.0;
   out_362240871876916223[312] = 0.0;
   out_362240871876916223[313] = 0.0;
   out_362240871876916223[314] = 0.0;
   out_362240871876916223[315] = 0.0;
   out_362240871876916223[316] = 0.0;
   out_362240871876916223[317] = 0.0;
   out_362240871876916223[318] = 0.0;
   out_362240871876916223[319] = 0.0;
   out_362240871876916223[320] = 0.0;
   out_362240871876916223[321] = 0.0;
   out_362240871876916223[322] = 0.0;
   out_362240871876916223[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_844759421205290898) {
   out_844759421205290898[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_844759421205290898[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_844759421205290898[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_844759421205290898[3] = dt*state[12] + state[3];
   out_844759421205290898[4] = dt*state[13] + state[4];
   out_844759421205290898[5] = dt*state[14] + state[5];
   out_844759421205290898[6] = state[6];
   out_844759421205290898[7] = state[7];
   out_844759421205290898[8] = state[8];
   out_844759421205290898[9] = state[9];
   out_844759421205290898[10] = state[10];
   out_844759421205290898[11] = state[11];
   out_844759421205290898[12] = state[12];
   out_844759421205290898[13] = state[13];
   out_844759421205290898[14] = state[14];
   out_844759421205290898[15] = state[15];
   out_844759421205290898[16] = state[16];
   out_844759421205290898[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3409614379123282877) {
   out_3409614379123282877[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3409614379123282877[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3409614379123282877[2] = 0;
   out_3409614379123282877[3] = 0;
   out_3409614379123282877[4] = 0;
   out_3409614379123282877[5] = 0;
   out_3409614379123282877[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3409614379123282877[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3409614379123282877[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3409614379123282877[9] = 0;
   out_3409614379123282877[10] = 0;
   out_3409614379123282877[11] = 0;
   out_3409614379123282877[12] = 0;
   out_3409614379123282877[13] = 0;
   out_3409614379123282877[14] = 0;
   out_3409614379123282877[15] = 0;
   out_3409614379123282877[16] = 0;
   out_3409614379123282877[17] = 0;
   out_3409614379123282877[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3409614379123282877[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3409614379123282877[20] = 0;
   out_3409614379123282877[21] = 0;
   out_3409614379123282877[22] = 0;
   out_3409614379123282877[23] = 0;
   out_3409614379123282877[24] = 0;
   out_3409614379123282877[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3409614379123282877[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3409614379123282877[27] = 0;
   out_3409614379123282877[28] = 0;
   out_3409614379123282877[29] = 0;
   out_3409614379123282877[30] = 0;
   out_3409614379123282877[31] = 0;
   out_3409614379123282877[32] = 0;
   out_3409614379123282877[33] = 0;
   out_3409614379123282877[34] = 0;
   out_3409614379123282877[35] = 0;
   out_3409614379123282877[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3409614379123282877[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3409614379123282877[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3409614379123282877[39] = 0;
   out_3409614379123282877[40] = 0;
   out_3409614379123282877[41] = 0;
   out_3409614379123282877[42] = 0;
   out_3409614379123282877[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3409614379123282877[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3409614379123282877[45] = 0;
   out_3409614379123282877[46] = 0;
   out_3409614379123282877[47] = 0;
   out_3409614379123282877[48] = 0;
   out_3409614379123282877[49] = 0;
   out_3409614379123282877[50] = 0;
   out_3409614379123282877[51] = 0;
   out_3409614379123282877[52] = 0;
   out_3409614379123282877[53] = 0;
   out_3409614379123282877[54] = 0;
   out_3409614379123282877[55] = 0;
   out_3409614379123282877[56] = 0;
   out_3409614379123282877[57] = 1;
   out_3409614379123282877[58] = 0;
   out_3409614379123282877[59] = 0;
   out_3409614379123282877[60] = 0;
   out_3409614379123282877[61] = 0;
   out_3409614379123282877[62] = 0;
   out_3409614379123282877[63] = 0;
   out_3409614379123282877[64] = 0;
   out_3409614379123282877[65] = 0;
   out_3409614379123282877[66] = dt;
   out_3409614379123282877[67] = 0;
   out_3409614379123282877[68] = 0;
   out_3409614379123282877[69] = 0;
   out_3409614379123282877[70] = 0;
   out_3409614379123282877[71] = 0;
   out_3409614379123282877[72] = 0;
   out_3409614379123282877[73] = 0;
   out_3409614379123282877[74] = 0;
   out_3409614379123282877[75] = 0;
   out_3409614379123282877[76] = 1;
   out_3409614379123282877[77] = 0;
   out_3409614379123282877[78] = 0;
   out_3409614379123282877[79] = 0;
   out_3409614379123282877[80] = 0;
   out_3409614379123282877[81] = 0;
   out_3409614379123282877[82] = 0;
   out_3409614379123282877[83] = 0;
   out_3409614379123282877[84] = 0;
   out_3409614379123282877[85] = dt;
   out_3409614379123282877[86] = 0;
   out_3409614379123282877[87] = 0;
   out_3409614379123282877[88] = 0;
   out_3409614379123282877[89] = 0;
   out_3409614379123282877[90] = 0;
   out_3409614379123282877[91] = 0;
   out_3409614379123282877[92] = 0;
   out_3409614379123282877[93] = 0;
   out_3409614379123282877[94] = 0;
   out_3409614379123282877[95] = 1;
   out_3409614379123282877[96] = 0;
   out_3409614379123282877[97] = 0;
   out_3409614379123282877[98] = 0;
   out_3409614379123282877[99] = 0;
   out_3409614379123282877[100] = 0;
   out_3409614379123282877[101] = 0;
   out_3409614379123282877[102] = 0;
   out_3409614379123282877[103] = 0;
   out_3409614379123282877[104] = dt;
   out_3409614379123282877[105] = 0;
   out_3409614379123282877[106] = 0;
   out_3409614379123282877[107] = 0;
   out_3409614379123282877[108] = 0;
   out_3409614379123282877[109] = 0;
   out_3409614379123282877[110] = 0;
   out_3409614379123282877[111] = 0;
   out_3409614379123282877[112] = 0;
   out_3409614379123282877[113] = 0;
   out_3409614379123282877[114] = 1;
   out_3409614379123282877[115] = 0;
   out_3409614379123282877[116] = 0;
   out_3409614379123282877[117] = 0;
   out_3409614379123282877[118] = 0;
   out_3409614379123282877[119] = 0;
   out_3409614379123282877[120] = 0;
   out_3409614379123282877[121] = 0;
   out_3409614379123282877[122] = 0;
   out_3409614379123282877[123] = 0;
   out_3409614379123282877[124] = 0;
   out_3409614379123282877[125] = 0;
   out_3409614379123282877[126] = 0;
   out_3409614379123282877[127] = 0;
   out_3409614379123282877[128] = 0;
   out_3409614379123282877[129] = 0;
   out_3409614379123282877[130] = 0;
   out_3409614379123282877[131] = 0;
   out_3409614379123282877[132] = 0;
   out_3409614379123282877[133] = 1;
   out_3409614379123282877[134] = 0;
   out_3409614379123282877[135] = 0;
   out_3409614379123282877[136] = 0;
   out_3409614379123282877[137] = 0;
   out_3409614379123282877[138] = 0;
   out_3409614379123282877[139] = 0;
   out_3409614379123282877[140] = 0;
   out_3409614379123282877[141] = 0;
   out_3409614379123282877[142] = 0;
   out_3409614379123282877[143] = 0;
   out_3409614379123282877[144] = 0;
   out_3409614379123282877[145] = 0;
   out_3409614379123282877[146] = 0;
   out_3409614379123282877[147] = 0;
   out_3409614379123282877[148] = 0;
   out_3409614379123282877[149] = 0;
   out_3409614379123282877[150] = 0;
   out_3409614379123282877[151] = 0;
   out_3409614379123282877[152] = 1;
   out_3409614379123282877[153] = 0;
   out_3409614379123282877[154] = 0;
   out_3409614379123282877[155] = 0;
   out_3409614379123282877[156] = 0;
   out_3409614379123282877[157] = 0;
   out_3409614379123282877[158] = 0;
   out_3409614379123282877[159] = 0;
   out_3409614379123282877[160] = 0;
   out_3409614379123282877[161] = 0;
   out_3409614379123282877[162] = 0;
   out_3409614379123282877[163] = 0;
   out_3409614379123282877[164] = 0;
   out_3409614379123282877[165] = 0;
   out_3409614379123282877[166] = 0;
   out_3409614379123282877[167] = 0;
   out_3409614379123282877[168] = 0;
   out_3409614379123282877[169] = 0;
   out_3409614379123282877[170] = 0;
   out_3409614379123282877[171] = 1;
   out_3409614379123282877[172] = 0;
   out_3409614379123282877[173] = 0;
   out_3409614379123282877[174] = 0;
   out_3409614379123282877[175] = 0;
   out_3409614379123282877[176] = 0;
   out_3409614379123282877[177] = 0;
   out_3409614379123282877[178] = 0;
   out_3409614379123282877[179] = 0;
   out_3409614379123282877[180] = 0;
   out_3409614379123282877[181] = 0;
   out_3409614379123282877[182] = 0;
   out_3409614379123282877[183] = 0;
   out_3409614379123282877[184] = 0;
   out_3409614379123282877[185] = 0;
   out_3409614379123282877[186] = 0;
   out_3409614379123282877[187] = 0;
   out_3409614379123282877[188] = 0;
   out_3409614379123282877[189] = 0;
   out_3409614379123282877[190] = 1;
   out_3409614379123282877[191] = 0;
   out_3409614379123282877[192] = 0;
   out_3409614379123282877[193] = 0;
   out_3409614379123282877[194] = 0;
   out_3409614379123282877[195] = 0;
   out_3409614379123282877[196] = 0;
   out_3409614379123282877[197] = 0;
   out_3409614379123282877[198] = 0;
   out_3409614379123282877[199] = 0;
   out_3409614379123282877[200] = 0;
   out_3409614379123282877[201] = 0;
   out_3409614379123282877[202] = 0;
   out_3409614379123282877[203] = 0;
   out_3409614379123282877[204] = 0;
   out_3409614379123282877[205] = 0;
   out_3409614379123282877[206] = 0;
   out_3409614379123282877[207] = 0;
   out_3409614379123282877[208] = 0;
   out_3409614379123282877[209] = 1;
   out_3409614379123282877[210] = 0;
   out_3409614379123282877[211] = 0;
   out_3409614379123282877[212] = 0;
   out_3409614379123282877[213] = 0;
   out_3409614379123282877[214] = 0;
   out_3409614379123282877[215] = 0;
   out_3409614379123282877[216] = 0;
   out_3409614379123282877[217] = 0;
   out_3409614379123282877[218] = 0;
   out_3409614379123282877[219] = 0;
   out_3409614379123282877[220] = 0;
   out_3409614379123282877[221] = 0;
   out_3409614379123282877[222] = 0;
   out_3409614379123282877[223] = 0;
   out_3409614379123282877[224] = 0;
   out_3409614379123282877[225] = 0;
   out_3409614379123282877[226] = 0;
   out_3409614379123282877[227] = 0;
   out_3409614379123282877[228] = 1;
   out_3409614379123282877[229] = 0;
   out_3409614379123282877[230] = 0;
   out_3409614379123282877[231] = 0;
   out_3409614379123282877[232] = 0;
   out_3409614379123282877[233] = 0;
   out_3409614379123282877[234] = 0;
   out_3409614379123282877[235] = 0;
   out_3409614379123282877[236] = 0;
   out_3409614379123282877[237] = 0;
   out_3409614379123282877[238] = 0;
   out_3409614379123282877[239] = 0;
   out_3409614379123282877[240] = 0;
   out_3409614379123282877[241] = 0;
   out_3409614379123282877[242] = 0;
   out_3409614379123282877[243] = 0;
   out_3409614379123282877[244] = 0;
   out_3409614379123282877[245] = 0;
   out_3409614379123282877[246] = 0;
   out_3409614379123282877[247] = 1;
   out_3409614379123282877[248] = 0;
   out_3409614379123282877[249] = 0;
   out_3409614379123282877[250] = 0;
   out_3409614379123282877[251] = 0;
   out_3409614379123282877[252] = 0;
   out_3409614379123282877[253] = 0;
   out_3409614379123282877[254] = 0;
   out_3409614379123282877[255] = 0;
   out_3409614379123282877[256] = 0;
   out_3409614379123282877[257] = 0;
   out_3409614379123282877[258] = 0;
   out_3409614379123282877[259] = 0;
   out_3409614379123282877[260] = 0;
   out_3409614379123282877[261] = 0;
   out_3409614379123282877[262] = 0;
   out_3409614379123282877[263] = 0;
   out_3409614379123282877[264] = 0;
   out_3409614379123282877[265] = 0;
   out_3409614379123282877[266] = 1;
   out_3409614379123282877[267] = 0;
   out_3409614379123282877[268] = 0;
   out_3409614379123282877[269] = 0;
   out_3409614379123282877[270] = 0;
   out_3409614379123282877[271] = 0;
   out_3409614379123282877[272] = 0;
   out_3409614379123282877[273] = 0;
   out_3409614379123282877[274] = 0;
   out_3409614379123282877[275] = 0;
   out_3409614379123282877[276] = 0;
   out_3409614379123282877[277] = 0;
   out_3409614379123282877[278] = 0;
   out_3409614379123282877[279] = 0;
   out_3409614379123282877[280] = 0;
   out_3409614379123282877[281] = 0;
   out_3409614379123282877[282] = 0;
   out_3409614379123282877[283] = 0;
   out_3409614379123282877[284] = 0;
   out_3409614379123282877[285] = 1;
   out_3409614379123282877[286] = 0;
   out_3409614379123282877[287] = 0;
   out_3409614379123282877[288] = 0;
   out_3409614379123282877[289] = 0;
   out_3409614379123282877[290] = 0;
   out_3409614379123282877[291] = 0;
   out_3409614379123282877[292] = 0;
   out_3409614379123282877[293] = 0;
   out_3409614379123282877[294] = 0;
   out_3409614379123282877[295] = 0;
   out_3409614379123282877[296] = 0;
   out_3409614379123282877[297] = 0;
   out_3409614379123282877[298] = 0;
   out_3409614379123282877[299] = 0;
   out_3409614379123282877[300] = 0;
   out_3409614379123282877[301] = 0;
   out_3409614379123282877[302] = 0;
   out_3409614379123282877[303] = 0;
   out_3409614379123282877[304] = 1;
   out_3409614379123282877[305] = 0;
   out_3409614379123282877[306] = 0;
   out_3409614379123282877[307] = 0;
   out_3409614379123282877[308] = 0;
   out_3409614379123282877[309] = 0;
   out_3409614379123282877[310] = 0;
   out_3409614379123282877[311] = 0;
   out_3409614379123282877[312] = 0;
   out_3409614379123282877[313] = 0;
   out_3409614379123282877[314] = 0;
   out_3409614379123282877[315] = 0;
   out_3409614379123282877[316] = 0;
   out_3409614379123282877[317] = 0;
   out_3409614379123282877[318] = 0;
   out_3409614379123282877[319] = 0;
   out_3409614379123282877[320] = 0;
   out_3409614379123282877[321] = 0;
   out_3409614379123282877[322] = 0;
   out_3409614379123282877[323] = 1;
}
void h_4(double *state, double *unused, double *out_3761995773053554002) {
   out_3761995773053554002[0] = state[6] + state[9];
   out_3761995773053554002[1] = state[7] + state[10];
   out_3761995773053554002[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_4790277513162164512) {
   out_4790277513162164512[0] = 0;
   out_4790277513162164512[1] = 0;
   out_4790277513162164512[2] = 0;
   out_4790277513162164512[3] = 0;
   out_4790277513162164512[4] = 0;
   out_4790277513162164512[5] = 0;
   out_4790277513162164512[6] = 1;
   out_4790277513162164512[7] = 0;
   out_4790277513162164512[8] = 0;
   out_4790277513162164512[9] = 1;
   out_4790277513162164512[10] = 0;
   out_4790277513162164512[11] = 0;
   out_4790277513162164512[12] = 0;
   out_4790277513162164512[13] = 0;
   out_4790277513162164512[14] = 0;
   out_4790277513162164512[15] = 0;
   out_4790277513162164512[16] = 0;
   out_4790277513162164512[17] = 0;
   out_4790277513162164512[18] = 0;
   out_4790277513162164512[19] = 0;
   out_4790277513162164512[20] = 0;
   out_4790277513162164512[21] = 0;
   out_4790277513162164512[22] = 0;
   out_4790277513162164512[23] = 0;
   out_4790277513162164512[24] = 0;
   out_4790277513162164512[25] = 1;
   out_4790277513162164512[26] = 0;
   out_4790277513162164512[27] = 0;
   out_4790277513162164512[28] = 1;
   out_4790277513162164512[29] = 0;
   out_4790277513162164512[30] = 0;
   out_4790277513162164512[31] = 0;
   out_4790277513162164512[32] = 0;
   out_4790277513162164512[33] = 0;
   out_4790277513162164512[34] = 0;
   out_4790277513162164512[35] = 0;
   out_4790277513162164512[36] = 0;
   out_4790277513162164512[37] = 0;
   out_4790277513162164512[38] = 0;
   out_4790277513162164512[39] = 0;
   out_4790277513162164512[40] = 0;
   out_4790277513162164512[41] = 0;
   out_4790277513162164512[42] = 0;
   out_4790277513162164512[43] = 0;
   out_4790277513162164512[44] = 1;
   out_4790277513162164512[45] = 0;
   out_4790277513162164512[46] = 0;
   out_4790277513162164512[47] = 1;
   out_4790277513162164512[48] = 0;
   out_4790277513162164512[49] = 0;
   out_4790277513162164512[50] = 0;
   out_4790277513162164512[51] = 0;
   out_4790277513162164512[52] = 0;
   out_4790277513162164512[53] = 0;
}
void h_10(double *state, double *unused, double *out_1433439433765456745) {
   out_1433439433765456745[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1433439433765456745[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1433439433765456745[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2492873908575038793) {
   out_2492873908575038793[0] = 0;
   out_2492873908575038793[1] = 9.8100000000000005*cos(state[1]);
   out_2492873908575038793[2] = 0;
   out_2492873908575038793[3] = 0;
   out_2492873908575038793[4] = -state[8];
   out_2492873908575038793[5] = state[7];
   out_2492873908575038793[6] = 0;
   out_2492873908575038793[7] = state[5];
   out_2492873908575038793[8] = -state[4];
   out_2492873908575038793[9] = 0;
   out_2492873908575038793[10] = 0;
   out_2492873908575038793[11] = 0;
   out_2492873908575038793[12] = 1;
   out_2492873908575038793[13] = 0;
   out_2492873908575038793[14] = 0;
   out_2492873908575038793[15] = 1;
   out_2492873908575038793[16] = 0;
   out_2492873908575038793[17] = 0;
   out_2492873908575038793[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2492873908575038793[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2492873908575038793[20] = 0;
   out_2492873908575038793[21] = state[8];
   out_2492873908575038793[22] = 0;
   out_2492873908575038793[23] = -state[6];
   out_2492873908575038793[24] = -state[5];
   out_2492873908575038793[25] = 0;
   out_2492873908575038793[26] = state[3];
   out_2492873908575038793[27] = 0;
   out_2492873908575038793[28] = 0;
   out_2492873908575038793[29] = 0;
   out_2492873908575038793[30] = 0;
   out_2492873908575038793[31] = 1;
   out_2492873908575038793[32] = 0;
   out_2492873908575038793[33] = 0;
   out_2492873908575038793[34] = 1;
   out_2492873908575038793[35] = 0;
   out_2492873908575038793[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2492873908575038793[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2492873908575038793[38] = 0;
   out_2492873908575038793[39] = -state[7];
   out_2492873908575038793[40] = state[6];
   out_2492873908575038793[41] = 0;
   out_2492873908575038793[42] = state[4];
   out_2492873908575038793[43] = -state[3];
   out_2492873908575038793[44] = 0;
   out_2492873908575038793[45] = 0;
   out_2492873908575038793[46] = 0;
   out_2492873908575038793[47] = 0;
   out_2492873908575038793[48] = 0;
   out_2492873908575038793[49] = 0;
   out_2492873908575038793[50] = 1;
   out_2492873908575038793[51] = 0;
   out_2492873908575038793[52] = 0;
   out_2492873908575038793[53] = 1;
}
void h_13(double *state, double *unused, double *out_7701755112567992010) {
   out_7701755112567992010[0] = state[3];
   out_7701755112567992010[1] = state[4];
   out_7701755112567992010[2] = state[5];
}
void H_13(double *state, double *unused, double *out_8002551338494497313) {
   out_8002551338494497313[0] = 0;
   out_8002551338494497313[1] = 0;
   out_8002551338494497313[2] = 0;
   out_8002551338494497313[3] = 1;
   out_8002551338494497313[4] = 0;
   out_8002551338494497313[5] = 0;
   out_8002551338494497313[6] = 0;
   out_8002551338494497313[7] = 0;
   out_8002551338494497313[8] = 0;
   out_8002551338494497313[9] = 0;
   out_8002551338494497313[10] = 0;
   out_8002551338494497313[11] = 0;
   out_8002551338494497313[12] = 0;
   out_8002551338494497313[13] = 0;
   out_8002551338494497313[14] = 0;
   out_8002551338494497313[15] = 0;
   out_8002551338494497313[16] = 0;
   out_8002551338494497313[17] = 0;
   out_8002551338494497313[18] = 0;
   out_8002551338494497313[19] = 0;
   out_8002551338494497313[20] = 0;
   out_8002551338494497313[21] = 0;
   out_8002551338494497313[22] = 1;
   out_8002551338494497313[23] = 0;
   out_8002551338494497313[24] = 0;
   out_8002551338494497313[25] = 0;
   out_8002551338494497313[26] = 0;
   out_8002551338494497313[27] = 0;
   out_8002551338494497313[28] = 0;
   out_8002551338494497313[29] = 0;
   out_8002551338494497313[30] = 0;
   out_8002551338494497313[31] = 0;
   out_8002551338494497313[32] = 0;
   out_8002551338494497313[33] = 0;
   out_8002551338494497313[34] = 0;
   out_8002551338494497313[35] = 0;
   out_8002551338494497313[36] = 0;
   out_8002551338494497313[37] = 0;
   out_8002551338494497313[38] = 0;
   out_8002551338494497313[39] = 0;
   out_8002551338494497313[40] = 0;
   out_8002551338494497313[41] = 1;
   out_8002551338494497313[42] = 0;
   out_8002551338494497313[43] = 0;
   out_8002551338494497313[44] = 0;
   out_8002551338494497313[45] = 0;
   out_8002551338494497313[46] = 0;
   out_8002551338494497313[47] = 0;
   out_8002551338494497313[48] = 0;
   out_8002551338494497313[49] = 0;
   out_8002551338494497313[50] = 0;
   out_8002551338494497313[51] = 0;
   out_8002551338494497313[52] = 0;
   out_8002551338494497313[53] = 0;
}
void h_14(double *state, double *unused, double *out_3517024732190759371) {
   out_3517024732190759371[0] = state[6];
   out_3517024732190759371[1] = state[7];
   out_3517024732190759371[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1707489080866792216) {
   out_1707489080866792216[0] = 0;
   out_1707489080866792216[1] = 0;
   out_1707489080866792216[2] = 0;
   out_1707489080866792216[3] = 0;
   out_1707489080866792216[4] = 0;
   out_1707489080866792216[5] = 0;
   out_1707489080866792216[6] = 1;
   out_1707489080866792216[7] = 0;
   out_1707489080866792216[8] = 0;
   out_1707489080866792216[9] = 0;
   out_1707489080866792216[10] = 0;
   out_1707489080866792216[11] = 0;
   out_1707489080866792216[12] = 0;
   out_1707489080866792216[13] = 0;
   out_1707489080866792216[14] = 0;
   out_1707489080866792216[15] = 0;
   out_1707489080866792216[16] = 0;
   out_1707489080866792216[17] = 0;
   out_1707489080866792216[18] = 0;
   out_1707489080866792216[19] = 0;
   out_1707489080866792216[20] = 0;
   out_1707489080866792216[21] = 0;
   out_1707489080866792216[22] = 0;
   out_1707489080866792216[23] = 0;
   out_1707489080866792216[24] = 0;
   out_1707489080866792216[25] = 1;
   out_1707489080866792216[26] = 0;
   out_1707489080866792216[27] = 0;
   out_1707489080866792216[28] = 0;
   out_1707489080866792216[29] = 0;
   out_1707489080866792216[30] = 0;
   out_1707489080866792216[31] = 0;
   out_1707489080866792216[32] = 0;
   out_1707489080866792216[33] = 0;
   out_1707489080866792216[34] = 0;
   out_1707489080866792216[35] = 0;
   out_1707489080866792216[36] = 0;
   out_1707489080866792216[37] = 0;
   out_1707489080866792216[38] = 0;
   out_1707489080866792216[39] = 0;
   out_1707489080866792216[40] = 0;
   out_1707489080866792216[41] = 0;
   out_1707489080866792216[42] = 0;
   out_1707489080866792216[43] = 0;
   out_1707489080866792216[44] = 1;
   out_1707489080866792216[45] = 0;
   out_1707489080866792216[46] = 0;
   out_1707489080866792216[47] = 0;
   out_1707489080866792216[48] = 0;
   out_1707489080866792216[49] = 0;
   out_1707489080866792216[50] = 0;
   out_1707489080866792216[51] = 0;
   out_1707489080866792216[52] = 0;
   out_1707489080866792216[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_4038237010904669995) {
  err_fun(nom_x, delta_x, out_4038237010904669995);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2572217743337337909) {
  inv_err_fun(nom_x, true_x, out_2572217743337337909);
}
void pose_H_mod_fun(double *state, double *out_362240871876916223) {
  H_mod_fun(state, out_362240871876916223);
}
void pose_f_fun(double *state, double dt, double *out_844759421205290898) {
  f_fun(state,  dt, out_844759421205290898);
}
void pose_F_fun(double *state, double dt, double *out_3409614379123282877) {
  F_fun(state,  dt, out_3409614379123282877);
}
void pose_h_4(double *state, double *unused, double *out_3761995773053554002) {
  h_4(state, unused, out_3761995773053554002);
}
void pose_H_4(double *state, double *unused, double *out_4790277513162164512) {
  H_4(state, unused, out_4790277513162164512);
}
void pose_h_10(double *state, double *unused, double *out_1433439433765456745) {
  h_10(state, unused, out_1433439433765456745);
}
void pose_H_10(double *state, double *unused, double *out_2492873908575038793) {
  H_10(state, unused, out_2492873908575038793);
}
void pose_h_13(double *state, double *unused, double *out_7701755112567992010) {
  h_13(state, unused, out_7701755112567992010);
}
void pose_H_13(double *state, double *unused, double *out_8002551338494497313) {
  H_13(state, unused, out_8002551338494497313);
}
void pose_h_14(double *state, double *unused, double *out_3517024732190759371) {
  h_14(state, unused, out_3517024732190759371);
}
void pose_H_14(double *state, double *unused, double *out_1707489080866792216) {
  H_14(state, unused, out_1707489080866792216);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
