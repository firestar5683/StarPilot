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
void err_fun(double *nom_x, double *delta_x, double *out_3341780452292505997) {
   out_3341780452292505997[0] = delta_x[0] + nom_x[0];
   out_3341780452292505997[1] = delta_x[1] + nom_x[1];
   out_3341780452292505997[2] = delta_x[2] + nom_x[2];
   out_3341780452292505997[3] = delta_x[3] + nom_x[3];
   out_3341780452292505997[4] = delta_x[4] + nom_x[4];
   out_3341780452292505997[5] = delta_x[5] + nom_x[5];
   out_3341780452292505997[6] = delta_x[6] + nom_x[6];
   out_3341780452292505997[7] = delta_x[7] + nom_x[7];
   out_3341780452292505997[8] = delta_x[8] + nom_x[8];
   out_3341780452292505997[9] = delta_x[9] + nom_x[9];
   out_3341780452292505997[10] = delta_x[10] + nom_x[10];
   out_3341780452292505997[11] = delta_x[11] + nom_x[11];
   out_3341780452292505997[12] = delta_x[12] + nom_x[12];
   out_3341780452292505997[13] = delta_x[13] + nom_x[13];
   out_3341780452292505997[14] = delta_x[14] + nom_x[14];
   out_3341780452292505997[15] = delta_x[15] + nom_x[15];
   out_3341780452292505997[16] = delta_x[16] + nom_x[16];
   out_3341780452292505997[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5409150910353518766) {
   out_5409150910353518766[0] = -nom_x[0] + true_x[0];
   out_5409150910353518766[1] = -nom_x[1] + true_x[1];
   out_5409150910353518766[2] = -nom_x[2] + true_x[2];
   out_5409150910353518766[3] = -nom_x[3] + true_x[3];
   out_5409150910353518766[4] = -nom_x[4] + true_x[4];
   out_5409150910353518766[5] = -nom_x[5] + true_x[5];
   out_5409150910353518766[6] = -nom_x[6] + true_x[6];
   out_5409150910353518766[7] = -nom_x[7] + true_x[7];
   out_5409150910353518766[8] = -nom_x[8] + true_x[8];
   out_5409150910353518766[9] = -nom_x[9] + true_x[9];
   out_5409150910353518766[10] = -nom_x[10] + true_x[10];
   out_5409150910353518766[11] = -nom_x[11] + true_x[11];
   out_5409150910353518766[12] = -nom_x[12] + true_x[12];
   out_5409150910353518766[13] = -nom_x[13] + true_x[13];
   out_5409150910353518766[14] = -nom_x[14] + true_x[14];
   out_5409150910353518766[15] = -nom_x[15] + true_x[15];
   out_5409150910353518766[16] = -nom_x[16] + true_x[16];
   out_5409150910353518766[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8300172317114018464) {
   out_8300172317114018464[0] = 1.0;
   out_8300172317114018464[1] = 0.0;
   out_8300172317114018464[2] = 0.0;
   out_8300172317114018464[3] = 0.0;
   out_8300172317114018464[4] = 0.0;
   out_8300172317114018464[5] = 0.0;
   out_8300172317114018464[6] = 0.0;
   out_8300172317114018464[7] = 0.0;
   out_8300172317114018464[8] = 0.0;
   out_8300172317114018464[9] = 0.0;
   out_8300172317114018464[10] = 0.0;
   out_8300172317114018464[11] = 0.0;
   out_8300172317114018464[12] = 0.0;
   out_8300172317114018464[13] = 0.0;
   out_8300172317114018464[14] = 0.0;
   out_8300172317114018464[15] = 0.0;
   out_8300172317114018464[16] = 0.0;
   out_8300172317114018464[17] = 0.0;
   out_8300172317114018464[18] = 0.0;
   out_8300172317114018464[19] = 1.0;
   out_8300172317114018464[20] = 0.0;
   out_8300172317114018464[21] = 0.0;
   out_8300172317114018464[22] = 0.0;
   out_8300172317114018464[23] = 0.0;
   out_8300172317114018464[24] = 0.0;
   out_8300172317114018464[25] = 0.0;
   out_8300172317114018464[26] = 0.0;
   out_8300172317114018464[27] = 0.0;
   out_8300172317114018464[28] = 0.0;
   out_8300172317114018464[29] = 0.0;
   out_8300172317114018464[30] = 0.0;
   out_8300172317114018464[31] = 0.0;
   out_8300172317114018464[32] = 0.0;
   out_8300172317114018464[33] = 0.0;
   out_8300172317114018464[34] = 0.0;
   out_8300172317114018464[35] = 0.0;
   out_8300172317114018464[36] = 0.0;
   out_8300172317114018464[37] = 0.0;
   out_8300172317114018464[38] = 1.0;
   out_8300172317114018464[39] = 0.0;
   out_8300172317114018464[40] = 0.0;
   out_8300172317114018464[41] = 0.0;
   out_8300172317114018464[42] = 0.0;
   out_8300172317114018464[43] = 0.0;
   out_8300172317114018464[44] = 0.0;
   out_8300172317114018464[45] = 0.0;
   out_8300172317114018464[46] = 0.0;
   out_8300172317114018464[47] = 0.0;
   out_8300172317114018464[48] = 0.0;
   out_8300172317114018464[49] = 0.0;
   out_8300172317114018464[50] = 0.0;
   out_8300172317114018464[51] = 0.0;
   out_8300172317114018464[52] = 0.0;
   out_8300172317114018464[53] = 0.0;
   out_8300172317114018464[54] = 0.0;
   out_8300172317114018464[55] = 0.0;
   out_8300172317114018464[56] = 0.0;
   out_8300172317114018464[57] = 1.0;
   out_8300172317114018464[58] = 0.0;
   out_8300172317114018464[59] = 0.0;
   out_8300172317114018464[60] = 0.0;
   out_8300172317114018464[61] = 0.0;
   out_8300172317114018464[62] = 0.0;
   out_8300172317114018464[63] = 0.0;
   out_8300172317114018464[64] = 0.0;
   out_8300172317114018464[65] = 0.0;
   out_8300172317114018464[66] = 0.0;
   out_8300172317114018464[67] = 0.0;
   out_8300172317114018464[68] = 0.0;
   out_8300172317114018464[69] = 0.0;
   out_8300172317114018464[70] = 0.0;
   out_8300172317114018464[71] = 0.0;
   out_8300172317114018464[72] = 0.0;
   out_8300172317114018464[73] = 0.0;
   out_8300172317114018464[74] = 0.0;
   out_8300172317114018464[75] = 0.0;
   out_8300172317114018464[76] = 1.0;
   out_8300172317114018464[77] = 0.0;
   out_8300172317114018464[78] = 0.0;
   out_8300172317114018464[79] = 0.0;
   out_8300172317114018464[80] = 0.0;
   out_8300172317114018464[81] = 0.0;
   out_8300172317114018464[82] = 0.0;
   out_8300172317114018464[83] = 0.0;
   out_8300172317114018464[84] = 0.0;
   out_8300172317114018464[85] = 0.0;
   out_8300172317114018464[86] = 0.0;
   out_8300172317114018464[87] = 0.0;
   out_8300172317114018464[88] = 0.0;
   out_8300172317114018464[89] = 0.0;
   out_8300172317114018464[90] = 0.0;
   out_8300172317114018464[91] = 0.0;
   out_8300172317114018464[92] = 0.0;
   out_8300172317114018464[93] = 0.0;
   out_8300172317114018464[94] = 0.0;
   out_8300172317114018464[95] = 1.0;
   out_8300172317114018464[96] = 0.0;
   out_8300172317114018464[97] = 0.0;
   out_8300172317114018464[98] = 0.0;
   out_8300172317114018464[99] = 0.0;
   out_8300172317114018464[100] = 0.0;
   out_8300172317114018464[101] = 0.0;
   out_8300172317114018464[102] = 0.0;
   out_8300172317114018464[103] = 0.0;
   out_8300172317114018464[104] = 0.0;
   out_8300172317114018464[105] = 0.0;
   out_8300172317114018464[106] = 0.0;
   out_8300172317114018464[107] = 0.0;
   out_8300172317114018464[108] = 0.0;
   out_8300172317114018464[109] = 0.0;
   out_8300172317114018464[110] = 0.0;
   out_8300172317114018464[111] = 0.0;
   out_8300172317114018464[112] = 0.0;
   out_8300172317114018464[113] = 0.0;
   out_8300172317114018464[114] = 1.0;
   out_8300172317114018464[115] = 0.0;
   out_8300172317114018464[116] = 0.0;
   out_8300172317114018464[117] = 0.0;
   out_8300172317114018464[118] = 0.0;
   out_8300172317114018464[119] = 0.0;
   out_8300172317114018464[120] = 0.0;
   out_8300172317114018464[121] = 0.0;
   out_8300172317114018464[122] = 0.0;
   out_8300172317114018464[123] = 0.0;
   out_8300172317114018464[124] = 0.0;
   out_8300172317114018464[125] = 0.0;
   out_8300172317114018464[126] = 0.0;
   out_8300172317114018464[127] = 0.0;
   out_8300172317114018464[128] = 0.0;
   out_8300172317114018464[129] = 0.0;
   out_8300172317114018464[130] = 0.0;
   out_8300172317114018464[131] = 0.0;
   out_8300172317114018464[132] = 0.0;
   out_8300172317114018464[133] = 1.0;
   out_8300172317114018464[134] = 0.0;
   out_8300172317114018464[135] = 0.0;
   out_8300172317114018464[136] = 0.0;
   out_8300172317114018464[137] = 0.0;
   out_8300172317114018464[138] = 0.0;
   out_8300172317114018464[139] = 0.0;
   out_8300172317114018464[140] = 0.0;
   out_8300172317114018464[141] = 0.0;
   out_8300172317114018464[142] = 0.0;
   out_8300172317114018464[143] = 0.0;
   out_8300172317114018464[144] = 0.0;
   out_8300172317114018464[145] = 0.0;
   out_8300172317114018464[146] = 0.0;
   out_8300172317114018464[147] = 0.0;
   out_8300172317114018464[148] = 0.0;
   out_8300172317114018464[149] = 0.0;
   out_8300172317114018464[150] = 0.0;
   out_8300172317114018464[151] = 0.0;
   out_8300172317114018464[152] = 1.0;
   out_8300172317114018464[153] = 0.0;
   out_8300172317114018464[154] = 0.0;
   out_8300172317114018464[155] = 0.0;
   out_8300172317114018464[156] = 0.0;
   out_8300172317114018464[157] = 0.0;
   out_8300172317114018464[158] = 0.0;
   out_8300172317114018464[159] = 0.0;
   out_8300172317114018464[160] = 0.0;
   out_8300172317114018464[161] = 0.0;
   out_8300172317114018464[162] = 0.0;
   out_8300172317114018464[163] = 0.0;
   out_8300172317114018464[164] = 0.0;
   out_8300172317114018464[165] = 0.0;
   out_8300172317114018464[166] = 0.0;
   out_8300172317114018464[167] = 0.0;
   out_8300172317114018464[168] = 0.0;
   out_8300172317114018464[169] = 0.0;
   out_8300172317114018464[170] = 0.0;
   out_8300172317114018464[171] = 1.0;
   out_8300172317114018464[172] = 0.0;
   out_8300172317114018464[173] = 0.0;
   out_8300172317114018464[174] = 0.0;
   out_8300172317114018464[175] = 0.0;
   out_8300172317114018464[176] = 0.0;
   out_8300172317114018464[177] = 0.0;
   out_8300172317114018464[178] = 0.0;
   out_8300172317114018464[179] = 0.0;
   out_8300172317114018464[180] = 0.0;
   out_8300172317114018464[181] = 0.0;
   out_8300172317114018464[182] = 0.0;
   out_8300172317114018464[183] = 0.0;
   out_8300172317114018464[184] = 0.0;
   out_8300172317114018464[185] = 0.0;
   out_8300172317114018464[186] = 0.0;
   out_8300172317114018464[187] = 0.0;
   out_8300172317114018464[188] = 0.0;
   out_8300172317114018464[189] = 0.0;
   out_8300172317114018464[190] = 1.0;
   out_8300172317114018464[191] = 0.0;
   out_8300172317114018464[192] = 0.0;
   out_8300172317114018464[193] = 0.0;
   out_8300172317114018464[194] = 0.0;
   out_8300172317114018464[195] = 0.0;
   out_8300172317114018464[196] = 0.0;
   out_8300172317114018464[197] = 0.0;
   out_8300172317114018464[198] = 0.0;
   out_8300172317114018464[199] = 0.0;
   out_8300172317114018464[200] = 0.0;
   out_8300172317114018464[201] = 0.0;
   out_8300172317114018464[202] = 0.0;
   out_8300172317114018464[203] = 0.0;
   out_8300172317114018464[204] = 0.0;
   out_8300172317114018464[205] = 0.0;
   out_8300172317114018464[206] = 0.0;
   out_8300172317114018464[207] = 0.0;
   out_8300172317114018464[208] = 0.0;
   out_8300172317114018464[209] = 1.0;
   out_8300172317114018464[210] = 0.0;
   out_8300172317114018464[211] = 0.0;
   out_8300172317114018464[212] = 0.0;
   out_8300172317114018464[213] = 0.0;
   out_8300172317114018464[214] = 0.0;
   out_8300172317114018464[215] = 0.0;
   out_8300172317114018464[216] = 0.0;
   out_8300172317114018464[217] = 0.0;
   out_8300172317114018464[218] = 0.0;
   out_8300172317114018464[219] = 0.0;
   out_8300172317114018464[220] = 0.0;
   out_8300172317114018464[221] = 0.0;
   out_8300172317114018464[222] = 0.0;
   out_8300172317114018464[223] = 0.0;
   out_8300172317114018464[224] = 0.0;
   out_8300172317114018464[225] = 0.0;
   out_8300172317114018464[226] = 0.0;
   out_8300172317114018464[227] = 0.0;
   out_8300172317114018464[228] = 1.0;
   out_8300172317114018464[229] = 0.0;
   out_8300172317114018464[230] = 0.0;
   out_8300172317114018464[231] = 0.0;
   out_8300172317114018464[232] = 0.0;
   out_8300172317114018464[233] = 0.0;
   out_8300172317114018464[234] = 0.0;
   out_8300172317114018464[235] = 0.0;
   out_8300172317114018464[236] = 0.0;
   out_8300172317114018464[237] = 0.0;
   out_8300172317114018464[238] = 0.0;
   out_8300172317114018464[239] = 0.0;
   out_8300172317114018464[240] = 0.0;
   out_8300172317114018464[241] = 0.0;
   out_8300172317114018464[242] = 0.0;
   out_8300172317114018464[243] = 0.0;
   out_8300172317114018464[244] = 0.0;
   out_8300172317114018464[245] = 0.0;
   out_8300172317114018464[246] = 0.0;
   out_8300172317114018464[247] = 1.0;
   out_8300172317114018464[248] = 0.0;
   out_8300172317114018464[249] = 0.0;
   out_8300172317114018464[250] = 0.0;
   out_8300172317114018464[251] = 0.0;
   out_8300172317114018464[252] = 0.0;
   out_8300172317114018464[253] = 0.0;
   out_8300172317114018464[254] = 0.0;
   out_8300172317114018464[255] = 0.0;
   out_8300172317114018464[256] = 0.0;
   out_8300172317114018464[257] = 0.0;
   out_8300172317114018464[258] = 0.0;
   out_8300172317114018464[259] = 0.0;
   out_8300172317114018464[260] = 0.0;
   out_8300172317114018464[261] = 0.0;
   out_8300172317114018464[262] = 0.0;
   out_8300172317114018464[263] = 0.0;
   out_8300172317114018464[264] = 0.0;
   out_8300172317114018464[265] = 0.0;
   out_8300172317114018464[266] = 1.0;
   out_8300172317114018464[267] = 0.0;
   out_8300172317114018464[268] = 0.0;
   out_8300172317114018464[269] = 0.0;
   out_8300172317114018464[270] = 0.0;
   out_8300172317114018464[271] = 0.0;
   out_8300172317114018464[272] = 0.0;
   out_8300172317114018464[273] = 0.0;
   out_8300172317114018464[274] = 0.0;
   out_8300172317114018464[275] = 0.0;
   out_8300172317114018464[276] = 0.0;
   out_8300172317114018464[277] = 0.0;
   out_8300172317114018464[278] = 0.0;
   out_8300172317114018464[279] = 0.0;
   out_8300172317114018464[280] = 0.0;
   out_8300172317114018464[281] = 0.0;
   out_8300172317114018464[282] = 0.0;
   out_8300172317114018464[283] = 0.0;
   out_8300172317114018464[284] = 0.0;
   out_8300172317114018464[285] = 1.0;
   out_8300172317114018464[286] = 0.0;
   out_8300172317114018464[287] = 0.0;
   out_8300172317114018464[288] = 0.0;
   out_8300172317114018464[289] = 0.0;
   out_8300172317114018464[290] = 0.0;
   out_8300172317114018464[291] = 0.0;
   out_8300172317114018464[292] = 0.0;
   out_8300172317114018464[293] = 0.0;
   out_8300172317114018464[294] = 0.0;
   out_8300172317114018464[295] = 0.0;
   out_8300172317114018464[296] = 0.0;
   out_8300172317114018464[297] = 0.0;
   out_8300172317114018464[298] = 0.0;
   out_8300172317114018464[299] = 0.0;
   out_8300172317114018464[300] = 0.0;
   out_8300172317114018464[301] = 0.0;
   out_8300172317114018464[302] = 0.0;
   out_8300172317114018464[303] = 0.0;
   out_8300172317114018464[304] = 1.0;
   out_8300172317114018464[305] = 0.0;
   out_8300172317114018464[306] = 0.0;
   out_8300172317114018464[307] = 0.0;
   out_8300172317114018464[308] = 0.0;
   out_8300172317114018464[309] = 0.0;
   out_8300172317114018464[310] = 0.0;
   out_8300172317114018464[311] = 0.0;
   out_8300172317114018464[312] = 0.0;
   out_8300172317114018464[313] = 0.0;
   out_8300172317114018464[314] = 0.0;
   out_8300172317114018464[315] = 0.0;
   out_8300172317114018464[316] = 0.0;
   out_8300172317114018464[317] = 0.0;
   out_8300172317114018464[318] = 0.0;
   out_8300172317114018464[319] = 0.0;
   out_8300172317114018464[320] = 0.0;
   out_8300172317114018464[321] = 0.0;
   out_8300172317114018464[322] = 0.0;
   out_8300172317114018464[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4063489601932878054) {
   out_4063489601932878054[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4063489601932878054[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4063489601932878054[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4063489601932878054[3] = dt*state[12] + state[3];
   out_4063489601932878054[4] = dt*state[13] + state[4];
   out_4063489601932878054[5] = dt*state[14] + state[5];
   out_4063489601932878054[6] = state[6];
   out_4063489601932878054[7] = state[7];
   out_4063489601932878054[8] = state[8];
   out_4063489601932878054[9] = state[9];
   out_4063489601932878054[10] = state[10];
   out_4063489601932878054[11] = state[11];
   out_4063489601932878054[12] = state[12];
   out_4063489601932878054[13] = state[13];
   out_4063489601932878054[14] = state[14];
   out_4063489601932878054[15] = state[15];
   out_4063489601932878054[16] = state[16];
   out_4063489601932878054[17] = state[17];
}
void F_fun(double *state, double dt, double *out_493800117352810078) {
   out_493800117352810078[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_493800117352810078[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_493800117352810078[2] = 0;
   out_493800117352810078[3] = 0;
   out_493800117352810078[4] = 0;
   out_493800117352810078[5] = 0;
   out_493800117352810078[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_493800117352810078[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_493800117352810078[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_493800117352810078[9] = 0;
   out_493800117352810078[10] = 0;
   out_493800117352810078[11] = 0;
   out_493800117352810078[12] = 0;
   out_493800117352810078[13] = 0;
   out_493800117352810078[14] = 0;
   out_493800117352810078[15] = 0;
   out_493800117352810078[16] = 0;
   out_493800117352810078[17] = 0;
   out_493800117352810078[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_493800117352810078[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_493800117352810078[20] = 0;
   out_493800117352810078[21] = 0;
   out_493800117352810078[22] = 0;
   out_493800117352810078[23] = 0;
   out_493800117352810078[24] = 0;
   out_493800117352810078[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_493800117352810078[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_493800117352810078[27] = 0;
   out_493800117352810078[28] = 0;
   out_493800117352810078[29] = 0;
   out_493800117352810078[30] = 0;
   out_493800117352810078[31] = 0;
   out_493800117352810078[32] = 0;
   out_493800117352810078[33] = 0;
   out_493800117352810078[34] = 0;
   out_493800117352810078[35] = 0;
   out_493800117352810078[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_493800117352810078[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_493800117352810078[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_493800117352810078[39] = 0;
   out_493800117352810078[40] = 0;
   out_493800117352810078[41] = 0;
   out_493800117352810078[42] = 0;
   out_493800117352810078[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_493800117352810078[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_493800117352810078[45] = 0;
   out_493800117352810078[46] = 0;
   out_493800117352810078[47] = 0;
   out_493800117352810078[48] = 0;
   out_493800117352810078[49] = 0;
   out_493800117352810078[50] = 0;
   out_493800117352810078[51] = 0;
   out_493800117352810078[52] = 0;
   out_493800117352810078[53] = 0;
   out_493800117352810078[54] = 0;
   out_493800117352810078[55] = 0;
   out_493800117352810078[56] = 0;
   out_493800117352810078[57] = 1;
   out_493800117352810078[58] = 0;
   out_493800117352810078[59] = 0;
   out_493800117352810078[60] = 0;
   out_493800117352810078[61] = 0;
   out_493800117352810078[62] = 0;
   out_493800117352810078[63] = 0;
   out_493800117352810078[64] = 0;
   out_493800117352810078[65] = 0;
   out_493800117352810078[66] = dt;
   out_493800117352810078[67] = 0;
   out_493800117352810078[68] = 0;
   out_493800117352810078[69] = 0;
   out_493800117352810078[70] = 0;
   out_493800117352810078[71] = 0;
   out_493800117352810078[72] = 0;
   out_493800117352810078[73] = 0;
   out_493800117352810078[74] = 0;
   out_493800117352810078[75] = 0;
   out_493800117352810078[76] = 1;
   out_493800117352810078[77] = 0;
   out_493800117352810078[78] = 0;
   out_493800117352810078[79] = 0;
   out_493800117352810078[80] = 0;
   out_493800117352810078[81] = 0;
   out_493800117352810078[82] = 0;
   out_493800117352810078[83] = 0;
   out_493800117352810078[84] = 0;
   out_493800117352810078[85] = dt;
   out_493800117352810078[86] = 0;
   out_493800117352810078[87] = 0;
   out_493800117352810078[88] = 0;
   out_493800117352810078[89] = 0;
   out_493800117352810078[90] = 0;
   out_493800117352810078[91] = 0;
   out_493800117352810078[92] = 0;
   out_493800117352810078[93] = 0;
   out_493800117352810078[94] = 0;
   out_493800117352810078[95] = 1;
   out_493800117352810078[96] = 0;
   out_493800117352810078[97] = 0;
   out_493800117352810078[98] = 0;
   out_493800117352810078[99] = 0;
   out_493800117352810078[100] = 0;
   out_493800117352810078[101] = 0;
   out_493800117352810078[102] = 0;
   out_493800117352810078[103] = 0;
   out_493800117352810078[104] = dt;
   out_493800117352810078[105] = 0;
   out_493800117352810078[106] = 0;
   out_493800117352810078[107] = 0;
   out_493800117352810078[108] = 0;
   out_493800117352810078[109] = 0;
   out_493800117352810078[110] = 0;
   out_493800117352810078[111] = 0;
   out_493800117352810078[112] = 0;
   out_493800117352810078[113] = 0;
   out_493800117352810078[114] = 1;
   out_493800117352810078[115] = 0;
   out_493800117352810078[116] = 0;
   out_493800117352810078[117] = 0;
   out_493800117352810078[118] = 0;
   out_493800117352810078[119] = 0;
   out_493800117352810078[120] = 0;
   out_493800117352810078[121] = 0;
   out_493800117352810078[122] = 0;
   out_493800117352810078[123] = 0;
   out_493800117352810078[124] = 0;
   out_493800117352810078[125] = 0;
   out_493800117352810078[126] = 0;
   out_493800117352810078[127] = 0;
   out_493800117352810078[128] = 0;
   out_493800117352810078[129] = 0;
   out_493800117352810078[130] = 0;
   out_493800117352810078[131] = 0;
   out_493800117352810078[132] = 0;
   out_493800117352810078[133] = 1;
   out_493800117352810078[134] = 0;
   out_493800117352810078[135] = 0;
   out_493800117352810078[136] = 0;
   out_493800117352810078[137] = 0;
   out_493800117352810078[138] = 0;
   out_493800117352810078[139] = 0;
   out_493800117352810078[140] = 0;
   out_493800117352810078[141] = 0;
   out_493800117352810078[142] = 0;
   out_493800117352810078[143] = 0;
   out_493800117352810078[144] = 0;
   out_493800117352810078[145] = 0;
   out_493800117352810078[146] = 0;
   out_493800117352810078[147] = 0;
   out_493800117352810078[148] = 0;
   out_493800117352810078[149] = 0;
   out_493800117352810078[150] = 0;
   out_493800117352810078[151] = 0;
   out_493800117352810078[152] = 1;
   out_493800117352810078[153] = 0;
   out_493800117352810078[154] = 0;
   out_493800117352810078[155] = 0;
   out_493800117352810078[156] = 0;
   out_493800117352810078[157] = 0;
   out_493800117352810078[158] = 0;
   out_493800117352810078[159] = 0;
   out_493800117352810078[160] = 0;
   out_493800117352810078[161] = 0;
   out_493800117352810078[162] = 0;
   out_493800117352810078[163] = 0;
   out_493800117352810078[164] = 0;
   out_493800117352810078[165] = 0;
   out_493800117352810078[166] = 0;
   out_493800117352810078[167] = 0;
   out_493800117352810078[168] = 0;
   out_493800117352810078[169] = 0;
   out_493800117352810078[170] = 0;
   out_493800117352810078[171] = 1;
   out_493800117352810078[172] = 0;
   out_493800117352810078[173] = 0;
   out_493800117352810078[174] = 0;
   out_493800117352810078[175] = 0;
   out_493800117352810078[176] = 0;
   out_493800117352810078[177] = 0;
   out_493800117352810078[178] = 0;
   out_493800117352810078[179] = 0;
   out_493800117352810078[180] = 0;
   out_493800117352810078[181] = 0;
   out_493800117352810078[182] = 0;
   out_493800117352810078[183] = 0;
   out_493800117352810078[184] = 0;
   out_493800117352810078[185] = 0;
   out_493800117352810078[186] = 0;
   out_493800117352810078[187] = 0;
   out_493800117352810078[188] = 0;
   out_493800117352810078[189] = 0;
   out_493800117352810078[190] = 1;
   out_493800117352810078[191] = 0;
   out_493800117352810078[192] = 0;
   out_493800117352810078[193] = 0;
   out_493800117352810078[194] = 0;
   out_493800117352810078[195] = 0;
   out_493800117352810078[196] = 0;
   out_493800117352810078[197] = 0;
   out_493800117352810078[198] = 0;
   out_493800117352810078[199] = 0;
   out_493800117352810078[200] = 0;
   out_493800117352810078[201] = 0;
   out_493800117352810078[202] = 0;
   out_493800117352810078[203] = 0;
   out_493800117352810078[204] = 0;
   out_493800117352810078[205] = 0;
   out_493800117352810078[206] = 0;
   out_493800117352810078[207] = 0;
   out_493800117352810078[208] = 0;
   out_493800117352810078[209] = 1;
   out_493800117352810078[210] = 0;
   out_493800117352810078[211] = 0;
   out_493800117352810078[212] = 0;
   out_493800117352810078[213] = 0;
   out_493800117352810078[214] = 0;
   out_493800117352810078[215] = 0;
   out_493800117352810078[216] = 0;
   out_493800117352810078[217] = 0;
   out_493800117352810078[218] = 0;
   out_493800117352810078[219] = 0;
   out_493800117352810078[220] = 0;
   out_493800117352810078[221] = 0;
   out_493800117352810078[222] = 0;
   out_493800117352810078[223] = 0;
   out_493800117352810078[224] = 0;
   out_493800117352810078[225] = 0;
   out_493800117352810078[226] = 0;
   out_493800117352810078[227] = 0;
   out_493800117352810078[228] = 1;
   out_493800117352810078[229] = 0;
   out_493800117352810078[230] = 0;
   out_493800117352810078[231] = 0;
   out_493800117352810078[232] = 0;
   out_493800117352810078[233] = 0;
   out_493800117352810078[234] = 0;
   out_493800117352810078[235] = 0;
   out_493800117352810078[236] = 0;
   out_493800117352810078[237] = 0;
   out_493800117352810078[238] = 0;
   out_493800117352810078[239] = 0;
   out_493800117352810078[240] = 0;
   out_493800117352810078[241] = 0;
   out_493800117352810078[242] = 0;
   out_493800117352810078[243] = 0;
   out_493800117352810078[244] = 0;
   out_493800117352810078[245] = 0;
   out_493800117352810078[246] = 0;
   out_493800117352810078[247] = 1;
   out_493800117352810078[248] = 0;
   out_493800117352810078[249] = 0;
   out_493800117352810078[250] = 0;
   out_493800117352810078[251] = 0;
   out_493800117352810078[252] = 0;
   out_493800117352810078[253] = 0;
   out_493800117352810078[254] = 0;
   out_493800117352810078[255] = 0;
   out_493800117352810078[256] = 0;
   out_493800117352810078[257] = 0;
   out_493800117352810078[258] = 0;
   out_493800117352810078[259] = 0;
   out_493800117352810078[260] = 0;
   out_493800117352810078[261] = 0;
   out_493800117352810078[262] = 0;
   out_493800117352810078[263] = 0;
   out_493800117352810078[264] = 0;
   out_493800117352810078[265] = 0;
   out_493800117352810078[266] = 1;
   out_493800117352810078[267] = 0;
   out_493800117352810078[268] = 0;
   out_493800117352810078[269] = 0;
   out_493800117352810078[270] = 0;
   out_493800117352810078[271] = 0;
   out_493800117352810078[272] = 0;
   out_493800117352810078[273] = 0;
   out_493800117352810078[274] = 0;
   out_493800117352810078[275] = 0;
   out_493800117352810078[276] = 0;
   out_493800117352810078[277] = 0;
   out_493800117352810078[278] = 0;
   out_493800117352810078[279] = 0;
   out_493800117352810078[280] = 0;
   out_493800117352810078[281] = 0;
   out_493800117352810078[282] = 0;
   out_493800117352810078[283] = 0;
   out_493800117352810078[284] = 0;
   out_493800117352810078[285] = 1;
   out_493800117352810078[286] = 0;
   out_493800117352810078[287] = 0;
   out_493800117352810078[288] = 0;
   out_493800117352810078[289] = 0;
   out_493800117352810078[290] = 0;
   out_493800117352810078[291] = 0;
   out_493800117352810078[292] = 0;
   out_493800117352810078[293] = 0;
   out_493800117352810078[294] = 0;
   out_493800117352810078[295] = 0;
   out_493800117352810078[296] = 0;
   out_493800117352810078[297] = 0;
   out_493800117352810078[298] = 0;
   out_493800117352810078[299] = 0;
   out_493800117352810078[300] = 0;
   out_493800117352810078[301] = 0;
   out_493800117352810078[302] = 0;
   out_493800117352810078[303] = 0;
   out_493800117352810078[304] = 1;
   out_493800117352810078[305] = 0;
   out_493800117352810078[306] = 0;
   out_493800117352810078[307] = 0;
   out_493800117352810078[308] = 0;
   out_493800117352810078[309] = 0;
   out_493800117352810078[310] = 0;
   out_493800117352810078[311] = 0;
   out_493800117352810078[312] = 0;
   out_493800117352810078[313] = 0;
   out_493800117352810078[314] = 0;
   out_493800117352810078[315] = 0;
   out_493800117352810078[316] = 0;
   out_493800117352810078[317] = 0;
   out_493800117352810078[318] = 0;
   out_493800117352810078[319] = 0;
   out_493800117352810078[320] = 0;
   out_493800117352810078[321] = 0;
   out_493800117352810078[322] = 0;
   out_493800117352810078[323] = 1;
}
void h_4(double *state, double *unused, double *out_6026765849154187968) {
   out_6026765849154187968[0] = state[6] + state[9];
   out_6026765849154187968[1] = state[7] + state[10];
   out_6026765849154187968[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7102224835231120360) {
   out_7102224835231120360[0] = 0;
   out_7102224835231120360[1] = 0;
   out_7102224835231120360[2] = 0;
   out_7102224835231120360[3] = 0;
   out_7102224835231120360[4] = 0;
   out_7102224835231120360[5] = 0;
   out_7102224835231120360[6] = 1;
   out_7102224835231120360[7] = 0;
   out_7102224835231120360[8] = 0;
   out_7102224835231120360[9] = 1;
   out_7102224835231120360[10] = 0;
   out_7102224835231120360[11] = 0;
   out_7102224835231120360[12] = 0;
   out_7102224835231120360[13] = 0;
   out_7102224835231120360[14] = 0;
   out_7102224835231120360[15] = 0;
   out_7102224835231120360[16] = 0;
   out_7102224835231120360[17] = 0;
   out_7102224835231120360[18] = 0;
   out_7102224835231120360[19] = 0;
   out_7102224835231120360[20] = 0;
   out_7102224835231120360[21] = 0;
   out_7102224835231120360[22] = 0;
   out_7102224835231120360[23] = 0;
   out_7102224835231120360[24] = 0;
   out_7102224835231120360[25] = 1;
   out_7102224835231120360[26] = 0;
   out_7102224835231120360[27] = 0;
   out_7102224835231120360[28] = 1;
   out_7102224835231120360[29] = 0;
   out_7102224835231120360[30] = 0;
   out_7102224835231120360[31] = 0;
   out_7102224835231120360[32] = 0;
   out_7102224835231120360[33] = 0;
   out_7102224835231120360[34] = 0;
   out_7102224835231120360[35] = 0;
   out_7102224835231120360[36] = 0;
   out_7102224835231120360[37] = 0;
   out_7102224835231120360[38] = 0;
   out_7102224835231120360[39] = 0;
   out_7102224835231120360[40] = 0;
   out_7102224835231120360[41] = 0;
   out_7102224835231120360[42] = 0;
   out_7102224835231120360[43] = 0;
   out_7102224835231120360[44] = 1;
   out_7102224835231120360[45] = 0;
   out_7102224835231120360[46] = 0;
   out_7102224835231120360[47] = 1;
   out_7102224835231120360[48] = 0;
   out_7102224835231120360[49] = 0;
   out_7102224835231120360[50] = 0;
   out_7102224835231120360[51] = 0;
   out_7102224835231120360[52] = 0;
   out_7102224835231120360[53] = 0;
}
void h_10(double *state, double *unused, double *out_1866086890220189324) {
   out_1866086890220189324[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1866086890220189324[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1866086890220189324[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_834802170779042492) {
   out_834802170779042492[0] = 0;
   out_834802170779042492[1] = 9.8100000000000005*cos(state[1]);
   out_834802170779042492[2] = 0;
   out_834802170779042492[3] = 0;
   out_834802170779042492[4] = -state[8];
   out_834802170779042492[5] = state[7];
   out_834802170779042492[6] = 0;
   out_834802170779042492[7] = state[5];
   out_834802170779042492[8] = -state[4];
   out_834802170779042492[9] = 0;
   out_834802170779042492[10] = 0;
   out_834802170779042492[11] = 0;
   out_834802170779042492[12] = 1;
   out_834802170779042492[13] = 0;
   out_834802170779042492[14] = 0;
   out_834802170779042492[15] = 1;
   out_834802170779042492[16] = 0;
   out_834802170779042492[17] = 0;
   out_834802170779042492[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_834802170779042492[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_834802170779042492[20] = 0;
   out_834802170779042492[21] = state[8];
   out_834802170779042492[22] = 0;
   out_834802170779042492[23] = -state[6];
   out_834802170779042492[24] = -state[5];
   out_834802170779042492[25] = 0;
   out_834802170779042492[26] = state[3];
   out_834802170779042492[27] = 0;
   out_834802170779042492[28] = 0;
   out_834802170779042492[29] = 0;
   out_834802170779042492[30] = 0;
   out_834802170779042492[31] = 1;
   out_834802170779042492[32] = 0;
   out_834802170779042492[33] = 0;
   out_834802170779042492[34] = 1;
   out_834802170779042492[35] = 0;
   out_834802170779042492[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_834802170779042492[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_834802170779042492[38] = 0;
   out_834802170779042492[39] = -state[7];
   out_834802170779042492[40] = state[6];
   out_834802170779042492[41] = 0;
   out_834802170779042492[42] = state[4];
   out_834802170779042492[43] = -state[3];
   out_834802170779042492[44] = 0;
   out_834802170779042492[45] = 0;
   out_834802170779042492[46] = 0;
   out_834802170779042492[47] = 0;
   out_834802170779042492[48] = 0;
   out_834802170779042492[49] = 0;
   out_834802170779042492[50] = 1;
   out_834802170779042492[51] = 0;
   out_834802170779042492[52] = 0;
   out_834802170779042492[53] = 1;
}
void h_13(double *state, double *unused, double *out_4520826989648677276) {
   out_4520826989648677276[0] = state[3];
   out_4520826989648677276[1] = state[4];
   out_4520826989648677276[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3889951009898787559) {
   out_3889951009898787559[0] = 0;
   out_3889951009898787559[1] = 0;
   out_3889951009898787559[2] = 0;
   out_3889951009898787559[3] = 1;
   out_3889951009898787559[4] = 0;
   out_3889951009898787559[5] = 0;
   out_3889951009898787559[6] = 0;
   out_3889951009898787559[7] = 0;
   out_3889951009898787559[8] = 0;
   out_3889951009898787559[9] = 0;
   out_3889951009898787559[10] = 0;
   out_3889951009898787559[11] = 0;
   out_3889951009898787559[12] = 0;
   out_3889951009898787559[13] = 0;
   out_3889951009898787559[14] = 0;
   out_3889951009898787559[15] = 0;
   out_3889951009898787559[16] = 0;
   out_3889951009898787559[17] = 0;
   out_3889951009898787559[18] = 0;
   out_3889951009898787559[19] = 0;
   out_3889951009898787559[20] = 0;
   out_3889951009898787559[21] = 0;
   out_3889951009898787559[22] = 1;
   out_3889951009898787559[23] = 0;
   out_3889951009898787559[24] = 0;
   out_3889951009898787559[25] = 0;
   out_3889951009898787559[26] = 0;
   out_3889951009898787559[27] = 0;
   out_3889951009898787559[28] = 0;
   out_3889951009898787559[29] = 0;
   out_3889951009898787559[30] = 0;
   out_3889951009898787559[31] = 0;
   out_3889951009898787559[32] = 0;
   out_3889951009898787559[33] = 0;
   out_3889951009898787559[34] = 0;
   out_3889951009898787559[35] = 0;
   out_3889951009898787559[36] = 0;
   out_3889951009898787559[37] = 0;
   out_3889951009898787559[38] = 0;
   out_3889951009898787559[39] = 0;
   out_3889951009898787559[40] = 0;
   out_3889951009898787559[41] = 1;
   out_3889951009898787559[42] = 0;
   out_3889951009898787559[43] = 0;
   out_3889951009898787559[44] = 0;
   out_3889951009898787559[45] = 0;
   out_3889951009898787559[46] = 0;
   out_3889951009898787559[47] = 0;
   out_3889951009898787559[48] = 0;
   out_3889951009898787559[49] = 0;
   out_3889951009898787559[50] = 0;
   out_3889951009898787559[51] = 0;
   out_3889951009898787559[52] = 0;
   out_3889951009898787559[53] = 0;
}
void h_14(double *state, double *unused, double *out_733646167343188736) {
   out_733646167343188736[0] = state[6];
   out_733646167343188736[1] = state[7];
   out_733646167343188736[2] = state[8];
}
void H_14(double *state, double *unused, double *out_8261730806183058960) {
   out_8261730806183058960[0] = 0;
   out_8261730806183058960[1] = 0;
   out_8261730806183058960[2] = 0;
   out_8261730806183058960[3] = 0;
   out_8261730806183058960[4] = 0;
   out_8261730806183058960[5] = 0;
   out_8261730806183058960[6] = 1;
   out_8261730806183058960[7] = 0;
   out_8261730806183058960[8] = 0;
   out_8261730806183058960[9] = 0;
   out_8261730806183058960[10] = 0;
   out_8261730806183058960[11] = 0;
   out_8261730806183058960[12] = 0;
   out_8261730806183058960[13] = 0;
   out_8261730806183058960[14] = 0;
   out_8261730806183058960[15] = 0;
   out_8261730806183058960[16] = 0;
   out_8261730806183058960[17] = 0;
   out_8261730806183058960[18] = 0;
   out_8261730806183058960[19] = 0;
   out_8261730806183058960[20] = 0;
   out_8261730806183058960[21] = 0;
   out_8261730806183058960[22] = 0;
   out_8261730806183058960[23] = 0;
   out_8261730806183058960[24] = 0;
   out_8261730806183058960[25] = 1;
   out_8261730806183058960[26] = 0;
   out_8261730806183058960[27] = 0;
   out_8261730806183058960[28] = 0;
   out_8261730806183058960[29] = 0;
   out_8261730806183058960[30] = 0;
   out_8261730806183058960[31] = 0;
   out_8261730806183058960[32] = 0;
   out_8261730806183058960[33] = 0;
   out_8261730806183058960[34] = 0;
   out_8261730806183058960[35] = 0;
   out_8261730806183058960[36] = 0;
   out_8261730806183058960[37] = 0;
   out_8261730806183058960[38] = 0;
   out_8261730806183058960[39] = 0;
   out_8261730806183058960[40] = 0;
   out_8261730806183058960[41] = 0;
   out_8261730806183058960[42] = 0;
   out_8261730806183058960[43] = 0;
   out_8261730806183058960[44] = 1;
   out_8261730806183058960[45] = 0;
   out_8261730806183058960[46] = 0;
   out_8261730806183058960[47] = 0;
   out_8261730806183058960[48] = 0;
   out_8261730806183058960[49] = 0;
   out_8261730806183058960[50] = 0;
   out_8261730806183058960[51] = 0;
   out_8261730806183058960[52] = 0;
   out_8261730806183058960[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3341780452292505997) {
  err_fun(nom_x, delta_x, out_3341780452292505997);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5409150910353518766) {
  inv_err_fun(nom_x, true_x, out_5409150910353518766);
}
void pose_H_mod_fun(double *state, double *out_8300172317114018464) {
  H_mod_fun(state, out_8300172317114018464);
}
void pose_f_fun(double *state, double dt, double *out_4063489601932878054) {
  f_fun(state,  dt, out_4063489601932878054);
}
void pose_F_fun(double *state, double dt, double *out_493800117352810078) {
  F_fun(state,  dt, out_493800117352810078);
}
void pose_h_4(double *state, double *unused, double *out_6026765849154187968) {
  h_4(state, unused, out_6026765849154187968);
}
void pose_H_4(double *state, double *unused, double *out_7102224835231120360) {
  H_4(state, unused, out_7102224835231120360);
}
void pose_h_10(double *state, double *unused, double *out_1866086890220189324) {
  h_10(state, unused, out_1866086890220189324);
}
void pose_H_10(double *state, double *unused, double *out_834802170779042492) {
  H_10(state, unused, out_834802170779042492);
}
void pose_h_13(double *state, double *unused, double *out_4520826989648677276) {
  h_13(state, unused, out_4520826989648677276);
}
void pose_H_13(double *state, double *unused, double *out_3889951009898787559) {
  H_13(state, unused, out_3889951009898787559);
}
void pose_h_14(double *state, double *unused, double *out_733646167343188736) {
  h_14(state, unused, out_733646167343188736);
}
void pose_H_14(double *state, double *unused, double *out_8261730806183058960) {
  H_14(state, unused, out_8261730806183058960);
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
