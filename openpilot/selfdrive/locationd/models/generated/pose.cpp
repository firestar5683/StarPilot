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
void err_fun(double *nom_x, double *delta_x, double *out_5239387107130576177) {
   out_5239387107130576177[0] = delta_x[0] + nom_x[0];
   out_5239387107130576177[1] = delta_x[1] + nom_x[1];
   out_5239387107130576177[2] = delta_x[2] + nom_x[2];
   out_5239387107130576177[3] = delta_x[3] + nom_x[3];
   out_5239387107130576177[4] = delta_x[4] + nom_x[4];
   out_5239387107130576177[5] = delta_x[5] + nom_x[5];
   out_5239387107130576177[6] = delta_x[6] + nom_x[6];
   out_5239387107130576177[7] = delta_x[7] + nom_x[7];
   out_5239387107130576177[8] = delta_x[8] + nom_x[8];
   out_5239387107130576177[9] = delta_x[9] + nom_x[9];
   out_5239387107130576177[10] = delta_x[10] + nom_x[10];
   out_5239387107130576177[11] = delta_x[11] + nom_x[11];
   out_5239387107130576177[12] = delta_x[12] + nom_x[12];
   out_5239387107130576177[13] = delta_x[13] + nom_x[13];
   out_5239387107130576177[14] = delta_x[14] + nom_x[14];
   out_5239387107130576177[15] = delta_x[15] + nom_x[15];
   out_5239387107130576177[16] = delta_x[16] + nom_x[16];
   out_5239387107130576177[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8017465374679690286) {
   out_8017465374679690286[0] = -nom_x[0] + true_x[0];
   out_8017465374679690286[1] = -nom_x[1] + true_x[1];
   out_8017465374679690286[2] = -nom_x[2] + true_x[2];
   out_8017465374679690286[3] = -nom_x[3] + true_x[3];
   out_8017465374679690286[4] = -nom_x[4] + true_x[4];
   out_8017465374679690286[5] = -nom_x[5] + true_x[5];
   out_8017465374679690286[6] = -nom_x[6] + true_x[6];
   out_8017465374679690286[7] = -nom_x[7] + true_x[7];
   out_8017465374679690286[8] = -nom_x[8] + true_x[8];
   out_8017465374679690286[9] = -nom_x[9] + true_x[9];
   out_8017465374679690286[10] = -nom_x[10] + true_x[10];
   out_8017465374679690286[11] = -nom_x[11] + true_x[11];
   out_8017465374679690286[12] = -nom_x[12] + true_x[12];
   out_8017465374679690286[13] = -nom_x[13] + true_x[13];
   out_8017465374679690286[14] = -nom_x[14] + true_x[14];
   out_8017465374679690286[15] = -nom_x[15] + true_x[15];
   out_8017465374679690286[16] = -nom_x[16] + true_x[16];
   out_8017465374679690286[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3050146727026118690) {
   out_3050146727026118690[0] = 1.0;
   out_3050146727026118690[1] = 0.0;
   out_3050146727026118690[2] = 0.0;
   out_3050146727026118690[3] = 0.0;
   out_3050146727026118690[4] = 0.0;
   out_3050146727026118690[5] = 0.0;
   out_3050146727026118690[6] = 0.0;
   out_3050146727026118690[7] = 0.0;
   out_3050146727026118690[8] = 0.0;
   out_3050146727026118690[9] = 0.0;
   out_3050146727026118690[10] = 0.0;
   out_3050146727026118690[11] = 0.0;
   out_3050146727026118690[12] = 0.0;
   out_3050146727026118690[13] = 0.0;
   out_3050146727026118690[14] = 0.0;
   out_3050146727026118690[15] = 0.0;
   out_3050146727026118690[16] = 0.0;
   out_3050146727026118690[17] = 0.0;
   out_3050146727026118690[18] = 0.0;
   out_3050146727026118690[19] = 1.0;
   out_3050146727026118690[20] = 0.0;
   out_3050146727026118690[21] = 0.0;
   out_3050146727026118690[22] = 0.0;
   out_3050146727026118690[23] = 0.0;
   out_3050146727026118690[24] = 0.0;
   out_3050146727026118690[25] = 0.0;
   out_3050146727026118690[26] = 0.0;
   out_3050146727026118690[27] = 0.0;
   out_3050146727026118690[28] = 0.0;
   out_3050146727026118690[29] = 0.0;
   out_3050146727026118690[30] = 0.0;
   out_3050146727026118690[31] = 0.0;
   out_3050146727026118690[32] = 0.0;
   out_3050146727026118690[33] = 0.0;
   out_3050146727026118690[34] = 0.0;
   out_3050146727026118690[35] = 0.0;
   out_3050146727026118690[36] = 0.0;
   out_3050146727026118690[37] = 0.0;
   out_3050146727026118690[38] = 1.0;
   out_3050146727026118690[39] = 0.0;
   out_3050146727026118690[40] = 0.0;
   out_3050146727026118690[41] = 0.0;
   out_3050146727026118690[42] = 0.0;
   out_3050146727026118690[43] = 0.0;
   out_3050146727026118690[44] = 0.0;
   out_3050146727026118690[45] = 0.0;
   out_3050146727026118690[46] = 0.0;
   out_3050146727026118690[47] = 0.0;
   out_3050146727026118690[48] = 0.0;
   out_3050146727026118690[49] = 0.0;
   out_3050146727026118690[50] = 0.0;
   out_3050146727026118690[51] = 0.0;
   out_3050146727026118690[52] = 0.0;
   out_3050146727026118690[53] = 0.0;
   out_3050146727026118690[54] = 0.0;
   out_3050146727026118690[55] = 0.0;
   out_3050146727026118690[56] = 0.0;
   out_3050146727026118690[57] = 1.0;
   out_3050146727026118690[58] = 0.0;
   out_3050146727026118690[59] = 0.0;
   out_3050146727026118690[60] = 0.0;
   out_3050146727026118690[61] = 0.0;
   out_3050146727026118690[62] = 0.0;
   out_3050146727026118690[63] = 0.0;
   out_3050146727026118690[64] = 0.0;
   out_3050146727026118690[65] = 0.0;
   out_3050146727026118690[66] = 0.0;
   out_3050146727026118690[67] = 0.0;
   out_3050146727026118690[68] = 0.0;
   out_3050146727026118690[69] = 0.0;
   out_3050146727026118690[70] = 0.0;
   out_3050146727026118690[71] = 0.0;
   out_3050146727026118690[72] = 0.0;
   out_3050146727026118690[73] = 0.0;
   out_3050146727026118690[74] = 0.0;
   out_3050146727026118690[75] = 0.0;
   out_3050146727026118690[76] = 1.0;
   out_3050146727026118690[77] = 0.0;
   out_3050146727026118690[78] = 0.0;
   out_3050146727026118690[79] = 0.0;
   out_3050146727026118690[80] = 0.0;
   out_3050146727026118690[81] = 0.0;
   out_3050146727026118690[82] = 0.0;
   out_3050146727026118690[83] = 0.0;
   out_3050146727026118690[84] = 0.0;
   out_3050146727026118690[85] = 0.0;
   out_3050146727026118690[86] = 0.0;
   out_3050146727026118690[87] = 0.0;
   out_3050146727026118690[88] = 0.0;
   out_3050146727026118690[89] = 0.0;
   out_3050146727026118690[90] = 0.0;
   out_3050146727026118690[91] = 0.0;
   out_3050146727026118690[92] = 0.0;
   out_3050146727026118690[93] = 0.0;
   out_3050146727026118690[94] = 0.0;
   out_3050146727026118690[95] = 1.0;
   out_3050146727026118690[96] = 0.0;
   out_3050146727026118690[97] = 0.0;
   out_3050146727026118690[98] = 0.0;
   out_3050146727026118690[99] = 0.0;
   out_3050146727026118690[100] = 0.0;
   out_3050146727026118690[101] = 0.0;
   out_3050146727026118690[102] = 0.0;
   out_3050146727026118690[103] = 0.0;
   out_3050146727026118690[104] = 0.0;
   out_3050146727026118690[105] = 0.0;
   out_3050146727026118690[106] = 0.0;
   out_3050146727026118690[107] = 0.0;
   out_3050146727026118690[108] = 0.0;
   out_3050146727026118690[109] = 0.0;
   out_3050146727026118690[110] = 0.0;
   out_3050146727026118690[111] = 0.0;
   out_3050146727026118690[112] = 0.0;
   out_3050146727026118690[113] = 0.0;
   out_3050146727026118690[114] = 1.0;
   out_3050146727026118690[115] = 0.0;
   out_3050146727026118690[116] = 0.0;
   out_3050146727026118690[117] = 0.0;
   out_3050146727026118690[118] = 0.0;
   out_3050146727026118690[119] = 0.0;
   out_3050146727026118690[120] = 0.0;
   out_3050146727026118690[121] = 0.0;
   out_3050146727026118690[122] = 0.0;
   out_3050146727026118690[123] = 0.0;
   out_3050146727026118690[124] = 0.0;
   out_3050146727026118690[125] = 0.0;
   out_3050146727026118690[126] = 0.0;
   out_3050146727026118690[127] = 0.0;
   out_3050146727026118690[128] = 0.0;
   out_3050146727026118690[129] = 0.0;
   out_3050146727026118690[130] = 0.0;
   out_3050146727026118690[131] = 0.0;
   out_3050146727026118690[132] = 0.0;
   out_3050146727026118690[133] = 1.0;
   out_3050146727026118690[134] = 0.0;
   out_3050146727026118690[135] = 0.0;
   out_3050146727026118690[136] = 0.0;
   out_3050146727026118690[137] = 0.0;
   out_3050146727026118690[138] = 0.0;
   out_3050146727026118690[139] = 0.0;
   out_3050146727026118690[140] = 0.0;
   out_3050146727026118690[141] = 0.0;
   out_3050146727026118690[142] = 0.0;
   out_3050146727026118690[143] = 0.0;
   out_3050146727026118690[144] = 0.0;
   out_3050146727026118690[145] = 0.0;
   out_3050146727026118690[146] = 0.0;
   out_3050146727026118690[147] = 0.0;
   out_3050146727026118690[148] = 0.0;
   out_3050146727026118690[149] = 0.0;
   out_3050146727026118690[150] = 0.0;
   out_3050146727026118690[151] = 0.0;
   out_3050146727026118690[152] = 1.0;
   out_3050146727026118690[153] = 0.0;
   out_3050146727026118690[154] = 0.0;
   out_3050146727026118690[155] = 0.0;
   out_3050146727026118690[156] = 0.0;
   out_3050146727026118690[157] = 0.0;
   out_3050146727026118690[158] = 0.0;
   out_3050146727026118690[159] = 0.0;
   out_3050146727026118690[160] = 0.0;
   out_3050146727026118690[161] = 0.0;
   out_3050146727026118690[162] = 0.0;
   out_3050146727026118690[163] = 0.0;
   out_3050146727026118690[164] = 0.0;
   out_3050146727026118690[165] = 0.0;
   out_3050146727026118690[166] = 0.0;
   out_3050146727026118690[167] = 0.0;
   out_3050146727026118690[168] = 0.0;
   out_3050146727026118690[169] = 0.0;
   out_3050146727026118690[170] = 0.0;
   out_3050146727026118690[171] = 1.0;
   out_3050146727026118690[172] = 0.0;
   out_3050146727026118690[173] = 0.0;
   out_3050146727026118690[174] = 0.0;
   out_3050146727026118690[175] = 0.0;
   out_3050146727026118690[176] = 0.0;
   out_3050146727026118690[177] = 0.0;
   out_3050146727026118690[178] = 0.0;
   out_3050146727026118690[179] = 0.0;
   out_3050146727026118690[180] = 0.0;
   out_3050146727026118690[181] = 0.0;
   out_3050146727026118690[182] = 0.0;
   out_3050146727026118690[183] = 0.0;
   out_3050146727026118690[184] = 0.0;
   out_3050146727026118690[185] = 0.0;
   out_3050146727026118690[186] = 0.0;
   out_3050146727026118690[187] = 0.0;
   out_3050146727026118690[188] = 0.0;
   out_3050146727026118690[189] = 0.0;
   out_3050146727026118690[190] = 1.0;
   out_3050146727026118690[191] = 0.0;
   out_3050146727026118690[192] = 0.0;
   out_3050146727026118690[193] = 0.0;
   out_3050146727026118690[194] = 0.0;
   out_3050146727026118690[195] = 0.0;
   out_3050146727026118690[196] = 0.0;
   out_3050146727026118690[197] = 0.0;
   out_3050146727026118690[198] = 0.0;
   out_3050146727026118690[199] = 0.0;
   out_3050146727026118690[200] = 0.0;
   out_3050146727026118690[201] = 0.0;
   out_3050146727026118690[202] = 0.0;
   out_3050146727026118690[203] = 0.0;
   out_3050146727026118690[204] = 0.0;
   out_3050146727026118690[205] = 0.0;
   out_3050146727026118690[206] = 0.0;
   out_3050146727026118690[207] = 0.0;
   out_3050146727026118690[208] = 0.0;
   out_3050146727026118690[209] = 1.0;
   out_3050146727026118690[210] = 0.0;
   out_3050146727026118690[211] = 0.0;
   out_3050146727026118690[212] = 0.0;
   out_3050146727026118690[213] = 0.0;
   out_3050146727026118690[214] = 0.0;
   out_3050146727026118690[215] = 0.0;
   out_3050146727026118690[216] = 0.0;
   out_3050146727026118690[217] = 0.0;
   out_3050146727026118690[218] = 0.0;
   out_3050146727026118690[219] = 0.0;
   out_3050146727026118690[220] = 0.0;
   out_3050146727026118690[221] = 0.0;
   out_3050146727026118690[222] = 0.0;
   out_3050146727026118690[223] = 0.0;
   out_3050146727026118690[224] = 0.0;
   out_3050146727026118690[225] = 0.0;
   out_3050146727026118690[226] = 0.0;
   out_3050146727026118690[227] = 0.0;
   out_3050146727026118690[228] = 1.0;
   out_3050146727026118690[229] = 0.0;
   out_3050146727026118690[230] = 0.0;
   out_3050146727026118690[231] = 0.0;
   out_3050146727026118690[232] = 0.0;
   out_3050146727026118690[233] = 0.0;
   out_3050146727026118690[234] = 0.0;
   out_3050146727026118690[235] = 0.0;
   out_3050146727026118690[236] = 0.0;
   out_3050146727026118690[237] = 0.0;
   out_3050146727026118690[238] = 0.0;
   out_3050146727026118690[239] = 0.0;
   out_3050146727026118690[240] = 0.0;
   out_3050146727026118690[241] = 0.0;
   out_3050146727026118690[242] = 0.0;
   out_3050146727026118690[243] = 0.0;
   out_3050146727026118690[244] = 0.0;
   out_3050146727026118690[245] = 0.0;
   out_3050146727026118690[246] = 0.0;
   out_3050146727026118690[247] = 1.0;
   out_3050146727026118690[248] = 0.0;
   out_3050146727026118690[249] = 0.0;
   out_3050146727026118690[250] = 0.0;
   out_3050146727026118690[251] = 0.0;
   out_3050146727026118690[252] = 0.0;
   out_3050146727026118690[253] = 0.0;
   out_3050146727026118690[254] = 0.0;
   out_3050146727026118690[255] = 0.0;
   out_3050146727026118690[256] = 0.0;
   out_3050146727026118690[257] = 0.0;
   out_3050146727026118690[258] = 0.0;
   out_3050146727026118690[259] = 0.0;
   out_3050146727026118690[260] = 0.0;
   out_3050146727026118690[261] = 0.0;
   out_3050146727026118690[262] = 0.0;
   out_3050146727026118690[263] = 0.0;
   out_3050146727026118690[264] = 0.0;
   out_3050146727026118690[265] = 0.0;
   out_3050146727026118690[266] = 1.0;
   out_3050146727026118690[267] = 0.0;
   out_3050146727026118690[268] = 0.0;
   out_3050146727026118690[269] = 0.0;
   out_3050146727026118690[270] = 0.0;
   out_3050146727026118690[271] = 0.0;
   out_3050146727026118690[272] = 0.0;
   out_3050146727026118690[273] = 0.0;
   out_3050146727026118690[274] = 0.0;
   out_3050146727026118690[275] = 0.0;
   out_3050146727026118690[276] = 0.0;
   out_3050146727026118690[277] = 0.0;
   out_3050146727026118690[278] = 0.0;
   out_3050146727026118690[279] = 0.0;
   out_3050146727026118690[280] = 0.0;
   out_3050146727026118690[281] = 0.0;
   out_3050146727026118690[282] = 0.0;
   out_3050146727026118690[283] = 0.0;
   out_3050146727026118690[284] = 0.0;
   out_3050146727026118690[285] = 1.0;
   out_3050146727026118690[286] = 0.0;
   out_3050146727026118690[287] = 0.0;
   out_3050146727026118690[288] = 0.0;
   out_3050146727026118690[289] = 0.0;
   out_3050146727026118690[290] = 0.0;
   out_3050146727026118690[291] = 0.0;
   out_3050146727026118690[292] = 0.0;
   out_3050146727026118690[293] = 0.0;
   out_3050146727026118690[294] = 0.0;
   out_3050146727026118690[295] = 0.0;
   out_3050146727026118690[296] = 0.0;
   out_3050146727026118690[297] = 0.0;
   out_3050146727026118690[298] = 0.0;
   out_3050146727026118690[299] = 0.0;
   out_3050146727026118690[300] = 0.0;
   out_3050146727026118690[301] = 0.0;
   out_3050146727026118690[302] = 0.0;
   out_3050146727026118690[303] = 0.0;
   out_3050146727026118690[304] = 1.0;
   out_3050146727026118690[305] = 0.0;
   out_3050146727026118690[306] = 0.0;
   out_3050146727026118690[307] = 0.0;
   out_3050146727026118690[308] = 0.0;
   out_3050146727026118690[309] = 0.0;
   out_3050146727026118690[310] = 0.0;
   out_3050146727026118690[311] = 0.0;
   out_3050146727026118690[312] = 0.0;
   out_3050146727026118690[313] = 0.0;
   out_3050146727026118690[314] = 0.0;
   out_3050146727026118690[315] = 0.0;
   out_3050146727026118690[316] = 0.0;
   out_3050146727026118690[317] = 0.0;
   out_3050146727026118690[318] = 0.0;
   out_3050146727026118690[319] = 0.0;
   out_3050146727026118690[320] = 0.0;
   out_3050146727026118690[321] = 0.0;
   out_3050146727026118690[322] = 0.0;
   out_3050146727026118690[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_7401195424910099109) {
   out_7401195424910099109[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_7401195424910099109[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_7401195424910099109[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_7401195424910099109[3] = dt*state[12] + state[3];
   out_7401195424910099109[4] = dt*state[13] + state[4];
   out_7401195424910099109[5] = dt*state[14] + state[5];
   out_7401195424910099109[6] = state[6];
   out_7401195424910099109[7] = state[7];
   out_7401195424910099109[8] = state[8];
   out_7401195424910099109[9] = state[9];
   out_7401195424910099109[10] = state[10];
   out_7401195424910099109[11] = state[11];
   out_7401195424910099109[12] = state[12];
   out_7401195424910099109[13] = state[13];
   out_7401195424910099109[14] = state[14];
   out_7401195424910099109[15] = state[15];
   out_7401195424910099109[16] = state[16];
   out_7401195424910099109[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7953355824038160444) {
   out_7953355824038160444[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7953355824038160444[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7953355824038160444[2] = 0;
   out_7953355824038160444[3] = 0;
   out_7953355824038160444[4] = 0;
   out_7953355824038160444[5] = 0;
   out_7953355824038160444[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7953355824038160444[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7953355824038160444[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7953355824038160444[9] = 0;
   out_7953355824038160444[10] = 0;
   out_7953355824038160444[11] = 0;
   out_7953355824038160444[12] = 0;
   out_7953355824038160444[13] = 0;
   out_7953355824038160444[14] = 0;
   out_7953355824038160444[15] = 0;
   out_7953355824038160444[16] = 0;
   out_7953355824038160444[17] = 0;
   out_7953355824038160444[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7953355824038160444[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7953355824038160444[20] = 0;
   out_7953355824038160444[21] = 0;
   out_7953355824038160444[22] = 0;
   out_7953355824038160444[23] = 0;
   out_7953355824038160444[24] = 0;
   out_7953355824038160444[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7953355824038160444[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7953355824038160444[27] = 0;
   out_7953355824038160444[28] = 0;
   out_7953355824038160444[29] = 0;
   out_7953355824038160444[30] = 0;
   out_7953355824038160444[31] = 0;
   out_7953355824038160444[32] = 0;
   out_7953355824038160444[33] = 0;
   out_7953355824038160444[34] = 0;
   out_7953355824038160444[35] = 0;
   out_7953355824038160444[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7953355824038160444[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7953355824038160444[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7953355824038160444[39] = 0;
   out_7953355824038160444[40] = 0;
   out_7953355824038160444[41] = 0;
   out_7953355824038160444[42] = 0;
   out_7953355824038160444[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7953355824038160444[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7953355824038160444[45] = 0;
   out_7953355824038160444[46] = 0;
   out_7953355824038160444[47] = 0;
   out_7953355824038160444[48] = 0;
   out_7953355824038160444[49] = 0;
   out_7953355824038160444[50] = 0;
   out_7953355824038160444[51] = 0;
   out_7953355824038160444[52] = 0;
   out_7953355824038160444[53] = 0;
   out_7953355824038160444[54] = 0;
   out_7953355824038160444[55] = 0;
   out_7953355824038160444[56] = 0;
   out_7953355824038160444[57] = 1;
   out_7953355824038160444[58] = 0;
   out_7953355824038160444[59] = 0;
   out_7953355824038160444[60] = 0;
   out_7953355824038160444[61] = 0;
   out_7953355824038160444[62] = 0;
   out_7953355824038160444[63] = 0;
   out_7953355824038160444[64] = 0;
   out_7953355824038160444[65] = 0;
   out_7953355824038160444[66] = dt;
   out_7953355824038160444[67] = 0;
   out_7953355824038160444[68] = 0;
   out_7953355824038160444[69] = 0;
   out_7953355824038160444[70] = 0;
   out_7953355824038160444[71] = 0;
   out_7953355824038160444[72] = 0;
   out_7953355824038160444[73] = 0;
   out_7953355824038160444[74] = 0;
   out_7953355824038160444[75] = 0;
   out_7953355824038160444[76] = 1;
   out_7953355824038160444[77] = 0;
   out_7953355824038160444[78] = 0;
   out_7953355824038160444[79] = 0;
   out_7953355824038160444[80] = 0;
   out_7953355824038160444[81] = 0;
   out_7953355824038160444[82] = 0;
   out_7953355824038160444[83] = 0;
   out_7953355824038160444[84] = 0;
   out_7953355824038160444[85] = dt;
   out_7953355824038160444[86] = 0;
   out_7953355824038160444[87] = 0;
   out_7953355824038160444[88] = 0;
   out_7953355824038160444[89] = 0;
   out_7953355824038160444[90] = 0;
   out_7953355824038160444[91] = 0;
   out_7953355824038160444[92] = 0;
   out_7953355824038160444[93] = 0;
   out_7953355824038160444[94] = 0;
   out_7953355824038160444[95] = 1;
   out_7953355824038160444[96] = 0;
   out_7953355824038160444[97] = 0;
   out_7953355824038160444[98] = 0;
   out_7953355824038160444[99] = 0;
   out_7953355824038160444[100] = 0;
   out_7953355824038160444[101] = 0;
   out_7953355824038160444[102] = 0;
   out_7953355824038160444[103] = 0;
   out_7953355824038160444[104] = dt;
   out_7953355824038160444[105] = 0;
   out_7953355824038160444[106] = 0;
   out_7953355824038160444[107] = 0;
   out_7953355824038160444[108] = 0;
   out_7953355824038160444[109] = 0;
   out_7953355824038160444[110] = 0;
   out_7953355824038160444[111] = 0;
   out_7953355824038160444[112] = 0;
   out_7953355824038160444[113] = 0;
   out_7953355824038160444[114] = 1;
   out_7953355824038160444[115] = 0;
   out_7953355824038160444[116] = 0;
   out_7953355824038160444[117] = 0;
   out_7953355824038160444[118] = 0;
   out_7953355824038160444[119] = 0;
   out_7953355824038160444[120] = 0;
   out_7953355824038160444[121] = 0;
   out_7953355824038160444[122] = 0;
   out_7953355824038160444[123] = 0;
   out_7953355824038160444[124] = 0;
   out_7953355824038160444[125] = 0;
   out_7953355824038160444[126] = 0;
   out_7953355824038160444[127] = 0;
   out_7953355824038160444[128] = 0;
   out_7953355824038160444[129] = 0;
   out_7953355824038160444[130] = 0;
   out_7953355824038160444[131] = 0;
   out_7953355824038160444[132] = 0;
   out_7953355824038160444[133] = 1;
   out_7953355824038160444[134] = 0;
   out_7953355824038160444[135] = 0;
   out_7953355824038160444[136] = 0;
   out_7953355824038160444[137] = 0;
   out_7953355824038160444[138] = 0;
   out_7953355824038160444[139] = 0;
   out_7953355824038160444[140] = 0;
   out_7953355824038160444[141] = 0;
   out_7953355824038160444[142] = 0;
   out_7953355824038160444[143] = 0;
   out_7953355824038160444[144] = 0;
   out_7953355824038160444[145] = 0;
   out_7953355824038160444[146] = 0;
   out_7953355824038160444[147] = 0;
   out_7953355824038160444[148] = 0;
   out_7953355824038160444[149] = 0;
   out_7953355824038160444[150] = 0;
   out_7953355824038160444[151] = 0;
   out_7953355824038160444[152] = 1;
   out_7953355824038160444[153] = 0;
   out_7953355824038160444[154] = 0;
   out_7953355824038160444[155] = 0;
   out_7953355824038160444[156] = 0;
   out_7953355824038160444[157] = 0;
   out_7953355824038160444[158] = 0;
   out_7953355824038160444[159] = 0;
   out_7953355824038160444[160] = 0;
   out_7953355824038160444[161] = 0;
   out_7953355824038160444[162] = 0;
   out_7953355824038160444[163] = 0;
   out_7953355824038160444[164] = 0;
   out_7953355824038160444[165] = 0;
   out_7953355824038160444[166] = 0;
   out_7953355824038160444[167] = 0;
   out_7953355824038160444[168] = 0;
   out_7953355824038160444[169] = 0;
   out_7953355824038160444[170] = 0;
   out_7953355824038160444[171] = 1;
   out_7953355824038160444[172] = 0;
   out_7953355824038160444[173] = 0;
   out_7953355824038160444[174] = 0;
   out_7953355824038160444[175] = 0;
   out_7953355824038160444[176] = 0;
   out_7953355824038160444[177] = 0;
   out_7953355824038160444[178] = 0;
   out_7953355824038160444[179] = 0;
   out_7953355824038160444[180] = 0;
   out_7953355824038160444[181] = 0;
   out_7953355824038160444[182] = 0;
   out_7953355824038160444[183] = 0;
   out_7953355824038160444[184] = 0;
   out_7953355824038160444[185] = 0;
   out_7953355824038160444[186] = 0;
   out_7953355824038160444[187] = 0;
   out_7953355824038160444[188] = 0;
   out_7953355824038160444[189] = 0;
   out_7953355824038160444[190] = 1;
   out_7953355824038160444[191] = 0;
   out_7953355824038160444[192] = 0;
   out_7953355824038160444[193] = 0;
   out_7953355824038160444[194] = 0;
   out_7953355824038160444[195] = 0;
   out_7953355824038160444[196] = 0;
   out_7953355824038160444[197] = 0;
   out_7953355824038160444[198] = 0;
   out_7953355824038160444[199] = 0;
   out_7953355824038160444[200] = 0;
   out_7953355824038160444[201] = 0;
   out_7953355824038160444[202] = 0;
   out_7953355824038160444[203] = 0;
   out_7953355824038160444[204] = 0;
   out_7953355824038160444[205] = 0;
   out_7953355824038160444[206] = 0;
   out_7953355824038160444[207] = 0;
   out_7953355824038160444[208] = 0;
   out_7953355824038160444[209] = 1;
   out_7953355824038160444[210] = 0;
   out_7953355824038160444[211] = 0;
   out_7953355824038160444[212] = 0;
   out_7953355824038160444[213] = 0;
   out_7953355824038160444[214] = 0;
   out_7953355824038160444[215] = 0;
   out_7953355824038160444[216] = 0;
   out_7953355824038160444[217] = 0;
   out_7953355824038160444[218] = 0;
   out_7953355824038160444[219] = 0;
   out_7953355824038160444[220] = 0;
   out_7953355824038160444[221] = 0;
   out_7953355824038160444[222] = 0;
   out_7953355824038160444[223] = 0;
   out_7953355824038160444[224] = 0;
   out_7953355824038160444[225] = 0;
   out_7953355824038160444[226] = 0;
   out_7953355824038160444[227] = 0;
   out_7953355824038160444[228] = 1;
   out_7953355824038160444[229] = 0;
   out_7953355824038160444[230] = 0;
   out_7953355824038160444[231] = 0;
   out_7953355824038160444[232] = 0;
   out_7953355824038160444[233] = 0;
   out_7953355824038160444[234] = 0;
   out_7953355824038160444[235] = 0;
   out_7953355824038160444[236] = 0;
   out_7953355824038160444[237] = 0;
   out_7953355824038160444[238] = 0;
   out_7953355824038160444[239] = 0;
   out_7953355824038160444[240] = 0;
   out_7953355824038160444[241] = 0;
   out_7953355824038160444[242] = 0;
   out_7953355824038160444[243] = 0;
   out_7953355824038160444[244] = 0;
   out_7953355824038160444[245] = 0;
   out_7953355824038160444[246] = 0;
   out_7953355824038160444[247] = 1;
   out_7953355824038160444[248] = 0;
   out_7953355824038160444[249] = 0;
   out_7953355824038160444[250] = 0;
   out_7953355824038160444[251] = 0;
   out_7953355824038160444[252] = 0;
   out_7953355824038160444[253] = 0;
   out_7953355824038160444[254] = 0;
   out_7953355824038160444[255] = 0;
   out_7953355824038160444[256] = 0;
   out_7953355824038160444[257] = 0;
   out_7953355824038160444[258] = 0;
   out_7953355824038160444[259] = 0;
   out_7953355824038160444[260] = 0;
   out_7953355824038160444[261] = 0;
   out_7953355824038160444[262] = 0;
   out_7953355824038160444[263] = 0;
   out_7953355824038160444[264] = 0;
   out_7953355824038160444[265] = 0;
   out_7953355824038160444[266] = 1;
   out_7953355824038160444[267] = 0;
   out_7953355824038160444[268] = 0;
   out_7953355824038160444[269] = 0;
   out_7953355824038160444[270] = 0;
   out_7953355824038160444[271] = 0;
   out_7953355824038160444[272] = 0;
   out_7953355824038160444[273] = 0;
   out_7953355824038160444[274] = 0;
   out_7953355824038160444[275] = 0;
   out_7953355824038160444[276] = 0;
   out_7953355824038160444[277] = 0;
   out_7953355824038160444[278] = 0;
   out_7953355824038160444[279] = 0;
   out_7953355824038160444[280] = 0;
   out_7953355824038160444[281] = 0;
   out_7953355824038160444[282] = 0;
   out_7953355824038160444[283] = 0;
   out_7953355824038160444[284] = 0;
   out_7953355824038160444[285] = 1;
   out_7953355824038160444[286] = 0;
   out_7953355824038160444[287] = 0;
   out_7953355824038160444[288] = 0;
   out_7953355824038160444[289] = 0;
   out_7953355824038160444[290] = 0;
   out_7953355824038160444[291] = 0;
   out_7953355824038160444[292] = 0;
   out_7953355824038160444[293] = 0;
   out_7953355824038160444[294] = 0;
   out_7953355824038160444[295] = 0;
   out_7953355824038160444[296] = 0;
   out_7953355824038160444[297] = 0;
   out_7953355824038160444[298] = 0;
   out_7953355824038160444[299] = 0;
   out_7953355824038160444[300] = 0;
   out_7953355824038160444[301] = 0;
   out_7953355824038160444[302] = 0;
   out_7953355824038160444[303] = 0;
   out_7953355824038160444[304] = 1;
   out_7953355824038160444[305] = 0;
   out_7953355824038160444[306] = 0;
   out_7953355824038160444[307] = 0;
   out_7953355824038160444[308] = 0;
   out_7953355824038160444[309] = 0;
   out_7953355824038160444[310] = 0;
   out_7953355824038160444[311] = 0;
   out_7953355824038160444[312] = 0;
   out_7953355824038160444[313] = 0;
   out_7953355824038160444[314] = 0;
   out_7953355824038160444[315] = 0;
   out_7953355824038160444[316] = 0;
   out_7953355824038160444[317] = 0;
   out_7953355824038160444[318] = 0;
   out_7953355824038160444[319] = 0;
   out_7953355824038160444[320] = 0;
   out_7953355824038160444[321] = 0;
   out_7953355824038160444[322] = 0;
   out_7953355824038160444[323] = 1;
}
void h_4(double *state, double *unused, double *out_5685529689104176696) {
   out_5685529689104176696[0] = state[6] + state[9];
   out_5685529689104176696[1] = state[7] + state[10];
   out_5685529689104176696[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8898228533778077411) {
   out_8898228533778077411[0] = 0;
   out_8898228533778077411[1] = 0;
   out_8898228533778077411[2] = 0;
   out_8898228533778077411[3] = 0;
   out_8898228533778077411[4] = 0;
   out_8898228533778077411[5] = 0;
   out_8898228533778077411[6] = 1;
   out_8898228533778077411[7] = 0;
   out_8898228533778077411[8] = 0;
   out_8898228533778077411[9] = 1;
   out_8898228533778077411[10] = 0;
   out_8898228533778077411[11] = 0;
   out_8898228533778077411[12] = 0;
   out_8898228533778077411[13] = 0;
   out_8898228533778077411[14] = 0;
   out_8898228533778077411[15] = 0;
   out_8898228533778077411[16] = 0;
   out_8898228533778077411[17] = 0;
   out_8898228533778077411[18] = 0;
   out_8898228533778077411[19] = 0;
   out_8898228533778077411[20] = 0;
   out_8898228533778077411[21] = 0;
   out_8898228533778077411[22] = 0;
   out_8898228533778077411[23] = 0;
   out_8898228533778077411[24] = 0;
   out_8898228533778077411[25] = 1;
   out_8898228533778077411[26] = 0;
   out_8898228533778077411[27] = 0;
   out_8898228533778077411[28] = 1;
   out_8898228533778077411[29] = 0;
   out_8898228533778077411[30] = 0;
   out_8898228533778077411[31] = 0;
   out_8898228533778077411[32] = 0;
   out_8898228533778077411[33] = 0;
   out_8898228533778077411[34] = 0;
   out_8898228533778077411[35] = 0;
   out_8898228533778077411[36] = 0;
   out_8898228533778077411[37] = 0;
   out_8898228533778077411[38] = 0;
   out_8898228533778077411[39] = 0;
   out_8898228533778077411[40] = 0;
   out_8898228533778077411[41] = 0;
   out_8898228533778077411[42] = 0;
   out_8898228533778077411[43] = 0;
   out_8898228533778077411[44] = 1;
   out_8898228533778077411[45] = 0;
   out_8898228533778077411[46] = 0;
   out_8898228533778077411[47] = 1;
   out_8898228533778077411[48] = 0;
   out_8898228533778077411[49] = 0;
   out_8898228533778077411[50] = 0;
   out_8898228533778077411[51] = 0;
   out_8898228533778077411[52] = 0;
   out_8898228533778077411[53] = 0;
}
void h_10(double *state, double *unused, double *out_5395236827797613020) {
   out_5395236827797613020[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5395236827797613020[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5395236827797613020[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4460820551654126260) {
   out_4460820551654126260[0] = 0;
   out_4460820551654126260[1] = 9.8100000000000005*cos(state[1]);
   out_4460820551654126260[2] = 0;
   out_4460820551654126260[3] = 0;
   out_4460820551654126260[4] = -state[8];
   out_4460820551654126260[5] = state[7];
   out_4460820551654126260[6] = 0;
   out_4460820551654126260[7] = state[5];
   out_4460820551654126260[8] = -state[4];
   out_4460820551654126260[9] = 0;
   out_4460820551654126260[10] = 0;
   out_4460820551654126260[11] = 0;
   out_4460820551654126260[12] = 1;
   out_4460820551654126260[13] = 0;
   out_4460820551654126260[14] = 0;
   out_4460820551654126260[15] = 1;
   out_4460820551654126260[16] = 0;
   out_4460820551654126260[17] = 0;
   out_4460820551654126260[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4460820551654126260[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4460820551654126260[20] = 0;
   out_4460820551654126260[21] = state[8];
   out_4460820551654126260[22] = 0;
   out_4460820551654126260[23] = -state[6];
   out_4460820551654126260[24] = -state[5];
   out_4460820551654126260[25] = 0;
   out_4460820551654126260[26] = state[3];
   out_4460820551654126260[27] = 0;
   out_4460820551654126260[28] = 0;
   out_4460820551654126260[29] = 0;
   out_4460820551654126260[30] = 0;
   out_4460820551654126260[31] = 1;
   out_4460820551654126260[32] = 0;
   out_4460820551654126260[33] = 0;
   out_4460820551654126260[34] = 1;
   out_4460820551654126260[35] = 0;
   out_4460820551654126260[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4460820551654126260[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4460820551654126260[38] = 0;
   out_4460820551654126260[39] = -state[7];
   out_4460820551654126260[40] = state[6];
   out_4460820551654126260[41] = 0;
   out_4460820551654126260[42] = state[4];
   out_4460820551654126260[43] = -state[3];
   out_4460820551654126260[44] = 0;
   out_4460820551654126260[45] = 0;
   out_4460820551654126260[46] = 0;
   out_4460820551654126260[47] = 0;
   out_4460820551654126260[48] = 0;
   out_4460820551654126260[49] = 0;
   out_4460820551654126260[50] = 1;
   out_4460820551654126260[51] = 0;
   out_4460820551654126260[52] = 0;
   out_4460820551654126260[53] = 1;
}
void h_13(double *state, double *unused, double *out_5553209120626692209) {
   out_5553209120626692209[0] = state[3];
   out_5553209120626692209[1] = state[4];
   out_5553209120626692209[2] = state[5];
}
void H_13(double *state, double *unused, double *out_5685954708445744610) {
   out_5685954708445744610[0] = 0;
   out_5685954708445744610[1] = 0;
   out_5685954708445744610[2] = 0;
   out_5685954708445744610[3] = 1;
   out_5685954708445744610[4] = 0;
   out_5685954708445744610[5] = 0;
   out_5685954708445744610[6] = 0;
   out_5685954708445744610[7] = 0;
   out_5685954708445744610[8] = 0;
   out_5685954708445744610[9] = 0;
   out_5685954708445744610[10] = 0;
   out_5685954708445744610[11] = 0;
   out_5685954708445744610[12] = 0;
   out_5685954708445744610[13] = 0;
   out_5685954708445744610[14] = 0;
   out_5685954708445744610[15] = 0;
   out_5685954708445744610[16] = 0;
   out_5685954708445744610[17] = 0;
   out_5685954708445744610[18] = 0;
   out_5685954708445744610[19] = 0;
   out_5685954708445744610[20] = 0;
   out_5685954708445744610[21] = 0;
   out_5685954708445744610[22] = 1;
   out_5685954708445744610[23] = 0;
   out_5685954708445744610[24] = 0;
   out_5685954708445744610[25] = 0;
   out_5685954708445744610[26] = 0;
   out_5685954708445744610[27] = 0;
   out_5685954708445744610[28] = 0;
   out_5685954708445744610[29] = 0;
   out_5685954708445744610[30] = 0;
   out_5685954708445744610[31] = 0;
   out_5685954708445744610[32] = 0;
   out_5685954708445744610[33] = 0;
   out_5685954708445744610[34] = 0;
   out_5685954708445744610[35] = 0;
   out_5685954708445744610[36] = 0;
   out_5685954708445744610[37] = 0;
   out_5685954708445744610[38] = 0;
   out_5685954708445744610[39] = 0;
   out_5685954708445744610[40] = 0;
   out_5685954708445744610[41] = 1;
   out_5685954708445744610[42] = 0;
   out_5685954708445744610[43] = 0;
   out_5685954708445744610[44] = 0;
   out_5685954708445744610[45] = 0;
   out_5685954708445744610[46] = 0;
   out_5685954708445744610[47] = 0;
   out_5685954708445744610[48] = 0;
   out_5685954708445744610[49] = 0;
   out_5685954708445744610[50] = 0;
   out_5685954708445744610[51] = 0;
   out_5685954708445744610[52] = 0;
   out_5685954708445744610[53] = 0;
}
void h_14(double *state, double *unused, double *out_8764675248435452423) {
   out_8764675248435452423[0] = state[6];
   out_8764675248435452423[1] = state[7];
   out_8764675248435452423[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4934987677438592882) {
   out_4934987677438592882[0] = 0;
   out_4934987677438592882[1] = 0;
   out_4934987677438592882[2] = 0;
   out_4934987677438592882[3] = 0;
   out_4934987677438592882[4] = 0;
   out_4934987677438592882[5] = 0;
   out_4934987677438592882[6] = 1;
   out_4934987677438592882[7] = 0;
   out_4934987677438592882[8] = 0;
   out_4934987677438592882[9] = 0;
   out_4934987677438592882[10] = 0;
   out_4934987677438592882[11] = 0;
   out_4934987677438592882[12] = 0;
   out_4934987677438592882[13] = 0;
   out_4934987677438592882[14] = 0;
   out_4934987677438592882[15] = 0;
   out_4934987677438592882[16] = 0;
   out_4934987677438592882[17] = 0;
   out_4934987677438592882[18] = 0;
   out_4934987677438592882[19] = 0;
   out_4934987677438592882[20] = 0;
   out_4934987677438592882[21] = 0;
   out_4934987677438592882[22] = 0;
   out_4934987677438592882[23] = 0;
   out_4934987677438592882[24] = 0;
   out_4934987677438592882[25] = 1;
   out_4934987677438592882[26] = 0;
   out_4934987677438592882[27] = 0;
   out_4934987677438592882[28] = 0;
   out_4934987677438592882[29] = 0;
   out_4934987677438592882[30] = 0;
   out_4934987677438592882[31] = 0;
   out_4934987677438592882[32] = 0;
   out_4934987677438592882[33] = 0;
   out_4934987677438592882[34] = 0;
   out_4934987677438592882[35] = 0;
   out_4934987677438592882[36] = 0;
   out_4934987677438592882[37] = 0;
   out_4934987677438592882[38] = 0;
   out_4934987677438592882[39] = 0;
   out_4934987677438592882[40] = 0;
   out_4934987677438592882[41] = 0;
   out_4934987677438592882[42] = 0;
   out_4934987677438592882[43] = 0;
   out_4934987677438592882[44] = 1;
   out_4934987677438592882[45] = 0;
   out_4934987677438592882[46] = 0;
   out_4934987677438592882[47] = 0;
   out_4934987677438592882[48] = 0;
   out_4934987677438592882[49] = 0;
   out_4934987677438592882[50] = 0;
   out_4934987677438592882[51] = 0;
   out_4934987677438592882[52] = 0;
   out_4934987677438592882[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5239387107130576177) {
  err_fun(nom_x, delta_x, out_5239387107130576177);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8017465374679690286) {
  inv_err_fun(nom_x, true_x, out_8017465374679690286);
}
void pose_H_mod_fun(double *state, double *out_3050146727026118690) {
  H_mod_fun(state, out_3050146727026118690);
}
void pose_f_fun(double *state, double dt, double *out_7401195424910099109) {
  f_fun(state,  dt, out_7401195424910099109);
}
void pose_F_fun(double *state, double dt, double *out_7953355824038160444) {
  F_fun(state,  dt, out_7953355824038160444);
}
void pose_h_4(double *state, double *unused, double *out_5685529689104176696) {
  h_4(state, unused, out_5685529689104176696);
}
void pose_H_4(double *state, double *unused, double *out_8898228533778077411) {
  H_4(state, unused, out_8898228533778077411);
}
void pose_h_10(double *state, double *unused, double *out_5395236827797613020) {
  h_10(state, unused, out_5395236827797613020);
}
void pose_H_10(double *state, double *unused, double *out_4460820551654126260) {
  H_10(state, unused, out_4460820551654126260);
}
void pose_h_13(double *state, double *unused, double *out_5553209120626692209) {
  h_13(state, unused, out_5553209120626692209);
}
void pose_H_13(double *state, double *unused, double *out_5685954708445744610) {
  H_13(state, unused, out_5685954708445744610);
}
void pose_h_14(double *state, double *unused, double *out_8764675248435452423) {
  h_14(state, unused, out_8764675248435452423);
}
void pose_H_14(double *state, double *unused, double *out_4934987677438592882) {
  H_14(state, unused, out_4934987677438592882);
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
