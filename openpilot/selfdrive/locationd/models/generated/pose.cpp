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
void err_fun(double *nom_x, double *delta_x, double *out_5566842885647767369) {
   out_5566842885647767369[0] = delta_x[0] + nom_x[0];
   out_5566842885647767369[1] = delta_x[1] + nom_x[1];
   out_5566842885647767369[2] = delta_x[2] + nom_x[2];
   out_5566842885647767369[3] = delta_x[3] + nom_x[3];
   out_5566842885647767369[4] = delta_x[4] + nom_x[4];
   out_5566842885647767369[5] = delta_x[5] + nom_x[5];
   out_5566842885647767369[6] = delta_x[6] + nom_x[6];
   out_5566842885647767369[7] = delta_x[7] + nom_x[7];
   out_5566842885647767369[8] = delta_x[8] + nom_x[8];
   out_5566842885647767369[9] = delta_x[9] + nom_x[9];
   out_5566842885647767369[10] = delta_x[10] + nom_x[10];
   out_5566842885647767369[11] = delta_x[11] + nom_x[11];
   out_5566842885647767369[12] = delta_x[12] + nom_x[12];
   out_5566842885647767369[13] = delta_x[13] + nom_x[13];
   out_5566842885647767369[14] = delta_x[14] + nom_x[14];
   out_5566842885647767369[15] = delta_x[15] + nom_x[15];
   out_5566842885647767369[16] = delta_x[16] + nom_x[16];
   out_5566842885647767369[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7605915063363770360) {
   out_7605915063363770360[0] = -nom_x[0] + true_x[0];
   out_7605915063363770360[1] = -nom_x[1] + true_x[1];
   out_7605915063363770360[2] = -nom_x[2] + true_x[2];
   out_7605915063363770360[3] = -nom_x[3] + true_x[3];
   out_7605915063363770360[4] = -nom_x[4] + true_x[4];
   out_7605915063363770360[5] = -nom_x[5] + true_x[5];
   out_7605915063363770360[6] = -nom_x[6] + true_x[6];
   out_7605915063363770360[7] = -nom_x[7] + true_x[7];
   out_7605915063363770360[8] = -nom_x[8] + true_x[8];
   out_7605915063363770360[9] = -nom_x[9] + true_x[9];
   out_7605915063363770360[10] = -nom_x[10] + true_x[10];
   out_7605915063363770360[11] = -nom_x[11] + true_x[11];
   out_7605915063363770360[12] = -nom_x[12] + true_x[12];
   out_7605915063363770360[13] = -nom_x[13] + true_x[13];
   out_7605915063363770360[14] = -nom_x[14] + true_x[14];
   out_7605915063363770360[15] = -nom_x[15] + true_x[15];
   out_7605915063363770360[16] = -nom_x[16] + true_x[16];
   out_7605915063363770360[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_9174940369185036217) {
   out_9174940369185036217[0] = 1.0;
   out_9174940369185036217[1] = 0.0;
   out_9174940369185036217[2] = 0.0;
   out_9174940369185036217[3] = 0.0;
   out_9174940369185036217[4] = 0.0;
   out_9174940369185036217[5] = 0.0;
   out_9174940369185036217[6] = 0.0;
   out_9174940369185036217[7] = 0.0;
   out_9174940369185036217[8] = 0.0;
   out_9174940369185036217[9] = 0.0;
   out_9174940369185036217[10] = 0.0;
   out_9174940369185036217[11] = 0.0;
   out_9174940369185036217[12] = 0.0;
   out_9174940369185036217[13] = 0.0;
   out_9174940369185036217[14] = 0.0;
   out_9174940369185036217[15] = 0.0;
   out_9174940369185036217[16] = 0.0;
   out_9174940369185036217[17] = 0.0;
   out_9174940369185036217[18] = 0.0;
   out_9174940369185036217[19] = 1.0;
   out_9174940369185036217[20] = 0.0;
   out_9174940369185036217[21] = 0.0;
   out_9174940369185036217[22] = 0.0;
   out_9174940369185036217[23] = 0.0;
   out_9174940369185036217[24] = 0.0;
   out_9174940369185036217[25] = 0.0;
   out_9174940369185036217[26] = 0.0;
   out_9174940369185036217[27] = 0.0;
   out_9174940369185036217[28] = 0.0;
   out_9174940369185036217[29] = 0.0;
   out_9174940369185036217[30] = 0.0;
   out_9174940369185036217[31] = 0.0;
   out_9174940369185036217[32] = 0.0;
   out_9174940369185036217[33] = 0.0;
   out_9174940369185036217[34] = 0.0;
   out_9174940369185036217[35] = 0.0;
   out_9174940369185036217[36] = 0.0;
   out_9174940369185036217[37] = 0.0;
   out_9174940369185036217[38] = 1.0;
   out_9174940369185036217[39] = 0.0;
   out_9174940369185036217[40] = 0.0;
   out_9174940369185036217[41] = 0.0;
   out_9174940369185036217[42] = 0.0;
   out_9174940369185036217[43] = 0.0;
   out_9174940369185036217[44] = 0.0;
   out_9174940369185036217[45] = 0.0;
   out_9174940369185036217[46] = 0.0;
   out_9174940369185036217[47] = 0.0;
   out_9174940369185036217[48] = 0.0;
   out_9174940369185036217[49] = 0.0;
   out_9174940369185036217[50] = 0.0;
   out_9174940369185036217[51] = 0.0;
   out_9174940369185036217[52] = 0.0;
   out_9174940369185036217[53] = 0.0;
   out_9174940369185036217[54] = 0.0;
   out_9174940369185036217[55] = 0.0;
   out_9174940369185036217[56] = 0.0;
   out_9174940369185036217[57] = 1.0;
   out_9174940369185036217[58] = 0.0;
   out_9174940369185036217[59] = 0.0;
   out_9174940369185036217[60] = 0.0;
   out_9174940369185036217[61] = 0.0;
   out_9174940369185036217[62] = 0.0;
   out_9174940369185036217[63] = 0.0;
   out_9174940369185036217[64] = 0.0;
   out_9174940369185036217[65] = 0.0;
   out_9174940369185036217[66] = 0.0;
   out_9174940369185036217[67] = 0.0;
   out_9174940369185036217[68] = 0.0;
   out_9174940369185036217[69] = 0.0;
   out_9174940369185036217[70] = 0.0;
   out_9174940369185036217[71] = 0.0;
   out_9174940369185036217[72] = 0.0;
   out_9174940369185036217[73] = 0.0;
   out_9174940369185036217[74] = 0.0;
   out_9174940369185036217[75] = 0.0;
   out_9174940369185036217[76] = 1.0;
   out_9174940369185036217[77] = 0.0;
   out_9174940369185036217[78] = 0.0;
   out_9174940369185036217[79] = 0.0;
   out_9174940369185036217[80] = 0.0;
   out_9174940369185036217[81] = 0.0;
   out_9174940369185036217[82] = 0.0;
   out_9174940369185036217[83] = 0.0;
   out_9174940369185036217[84] = 0.0;
   out_9174940369185036217[85] = 0.0;
   out_9174940369185036217[86] = 0.0;
   out_9174940369185036217[87] = 0.0;
   out_9174940369185036217[88] = 0.0;
   out_9174940369185036217[89] = 0.0;
   out_9174940369185036217[90] = 0.0;
   out_9174940369185036217[91] = 0.0;
   out_9174940369185036217[92] = 0.0;
   out_9174940369185036217[93] = 0.0;
   out_9174940369185036217[94] = 0.0;
   out_9174940369185036217[95] = 1.0;
   out_9174940369185036217[96] = 0.0;
   out_9174940369185036217[97] = 0.0;
   out_9174940369185036217[98] = 0.0;
   out_9174940369185036217[99] = 0.0;
   out_9174940369185036217[100] = 0.0;
   out_9174940369185036217[101] = 0.0;
   out_9174940369185036217[102] = 0.0;
   out_9174940369185036217[103] = 0.0;
   out_9174940369185036217[104] = 0.0;
   out_9174940369185036217[105] = 0.0;
   out_9174940369185036217[106] = 0.0;
   out_9174940369185036217[107] = 0.0;
   out_9174940369185036217[108] = 0.0;
   out_9174940369185036217[109] = 0.0;
   out_9174940369185036217[110] = 0.0;
   out_9174940369185036217[111] = 0.0;
   out_9174940369185036217[112] = 0.0;
   out_9174940369185036217[113] = 0.0;
   out_9174940369185036217[114] = 1.0;
   out_9174940369185036217[115] = 0.0;
   out_9174940369185036217[116] = 0.0;
   out_9174940369185036217[117] = 0.0;
   out_9174940369185036217[118] = 0.0;
   out_9174940369185036217[119] = 0.0;
   out_9174940369185036217[120] = 0.0;
   out_9174940369185036217[121] = 0.0;
   out_9174940369185036217[122] = 0.0;
   out_9174940369185036217[123] = 0.0;
   out_9174940369185036217[124] = 0.0;
   out_9174940369185036217[125] = 0.0;
   out_9174940369185036217[126] = 0.0;
   out_9174940369185036217[127] = 0.0;
   out_9174940369185036217[128] = 0.0;
   out_9174940369185036217[129] = 0.0;
   out_9174940369185036217[130] = 0.0;
   out_9174940369185036217[131] = 0.0;
   out_9174940369185036217[132] = 0.0;
   out_9174940369185036217[133] = 1.0;
   out_9174940369185036217[134] = 0.0;
   out_9174940369185036217[135] = 0.0;
   out_9174940369185036217[136] = 0.0;
   out_9174940369185036217[137] = 0.0;
   out_9174940369185036217[138] = 0.0;
   out_9174940369185036217[139] = 0.0;
   out_9174940369185036217[140] = 0.0;
   out_9174940369185036217[141] = 0.0;
   out_9174940369185036217[142] = 0.0;
   out_9174940369185036217[143] = 0.0;
   out_9174940369185036217[144] = 0.0;
   out_9174940369185036217[145] = 0.0;
   out_9174940369185036217[146] = 0.0;
   out_9174940369185036217[147] = 0.0;
   out_9174940369185036217[148] = 0.0;
   out_9174940369185036217[149] = 0.0;
   out_9174940369185036217[150] = 0.0;
   out_9174940369185036217[151] = 0.0;
   out_9174940369185036217[152] = 1.0;
   out_9174940369185036217[153] = 0.0;
   out_9174940369185036217[154] = 0.0;
   out_9174940369185036217[155] = 0.0;
   out_9174940369185036217[156] = 0.0;
   out_9174940369185036217[157] = 0.0;
   out_9174940369185036217[158] = 0.0;
   out_9174940369185036217[159] = 0.0;
   out_9174940369185036217[160] = 0.0;
   out_9174940369185036217[161] = 0.0;
   out_9174940369185036217[162] = 0.0;
   out_9174940369185036217[163] = 0.0;
   out_9174940369185036217[164] = 0.0;
   out_9174940369185036217[165] = 0.0;
   out_9174940369185036217[166] = 0.0;
   out_9174940369185036217[167] = 0.0;
   out_9174940369185036217[168] = 0.0;
   out_9174940369185036217[169] = 0.0;
   out_9174940369185036217[170] = 0.0;
   out_9174940369185036217[171] = 1.0;
   out_9174940369185036217[172] = 0.0;
   out_9174940369185036217[173] = 0.0;
   out_9174940369185036217[174] = 0.0;
   out_9174940369185036217[175] = 0.0;
   out_9174940369185036217[176] = 0.0;
   out_9174940369185036217[177] = 0.0;
   out_9174940369185036217[178] = 0.0;
   out_9174940369185036217[179] = 0.0;
   out_9174940369185036217[180] = 0.0;
   out_9174940369185036217[181] = 0.0;
   out_9174940369185036217[182] = 0.0;
   out_9174940369185036217[183] = 0.0;
   out_9174940369185036217[184] = 0.0;
   out_9174940369185036217[185] = 0.0;
   out_9174940369185036217[186] = 0.0;
   out_9174940369185036217[187] = 0.0;
   out_9174940369185036217[188] = 0.0;
   out_9174940369185036217[189] = 0.0;
   out_9174940369185036217[190] = 1.0;
   out_9174940369185036217[191] = 0.0;
   out_9174940369185036217[192] = 0.0;
   out_9174940369185036217[193] = 0.0;
   out_9174940369185036217[194] = 0.0;
   out_9174940369185036217[195] = 0.0;
   out_9174940369185036217[196] = 0.0;
   out_9174940369185036217[197] = 0.0;
   out_9174940369185036217[198] = 0.0;
   out_9174940369185036217[199] = 0.0;
   out_9174940369185036217[200] = 0.0;
   out_9174940369185036217[201] = 0.0;
   out_9174940369185036217[202] = 0.0;
   out_9174940369185036217[203] = 0.0;
   out_9174940369185036217[204] = 0.0;
   out_9174940369185036217[205] = 0.0;
   out_9174940369185036217[206] = 0.0;
   out_9174940369185036217[207] = 0.0;
   out_9174940369185036217[208] = 0.0;
   out_9174940369185036217[209] = 1.0;
   out_9174940369185036217[210] = 0.0;
   out_9174940369185036217[211] = 0.0;
   out_9174940369185036217[212] = 0.0;
   out_9174940369185036217[213] = 0.0;
   out_9174940369185036217[214] = 0.0;
   out_9174940369185036217[215] = 0.0;
   out_9174940369185036217[216] = 0.0;
   out_9174940369185036217[217] = 0.0;
   out_9174940369185036217[218] = 0.0;
   out_9174940369185036217[219] = 0.0;
   out_9174940369185036217[220] = 0.0;
   out_9174940369185036217[221] = 0.0;
   out_9174940369185036217[222] = 0.0;
   out_9174940369185036217[223] = 0.0;
   out_9174940369185036217[224] = 0.0;
   out_9174940369185036217[225] = 0.0;
   out_9174940369185036217[226] = 0.0;
   out_9174940369185036217[227] = 0.0;
   out_9174940369185036217[228] = 1.0;
   out_9174940369185036217[229] = 0.0;
   out_9174940369185036217[230] = 0.0;
   out_9174940369185036217[231] = 0.0;
   out_9174940369185036217[232] = 0.0;
   out_9174940369185036217[233] = 0.0;
   out_9174940369185036217[234] = 0.0;
   out_9174940369185036217[235] = 0.0;
   out_9174940369185036217[236] = 0.0;
   out_9174940369185036217[237] = 0.0;
   out_9174940369185036217[238] = 0.0;
   out_9174940369185036217[239] = 0.0;
   out_9174940369185036217[240] = 0.0;
   out_9174940369185036217[241] = 0.0;
   out_9174940369185036217[242] = 0.0;
   out_9174940369185036217[243] = 0.0;
   out_9174940369185036217[244] = 0.0;
   out_9174940369185036217[245] = 0.0;
   out_9174940369185036217[246] = 0.0;
   out_9174940369185036217[247] = 1.0;
   out_9174940369185036217[248] = 0.0;
   out_9174940369185036217[249] = 0.0;
   out_9174940369185036217[250] = 0.0;
   out_9174940369185036217[251] = 0.0;
   out_9174940369185036217[252] = 0.0;
   out_9174940369185036217[253] = 0.0;
   out_9174940369185036217[254] = 0.0;
   out_9174940369185036217[255] = 0.0;
   out_9174940369185036217[256] = 0.0;
   out_9174940369185036217[257] = 0.0;
   out_9174940369185036217[258] = 0.0;
   out_9174940369185036217[259] = 0.0;
   out_9174940369185036217[260] = 0.0;
   out_9174940369185036217[261] = 0.0;
   out_9174940369185036217[262] = 0.0;
   out_9174940369185036217[263] = 0.0;
   out_9174940369185036217[264] = 0.0;
   out_9174940369185036217[265] = 0.0;
   out_9174940369185036217[266] = 1.0;
   out_9174940369185036217[267] = 0.0;
   out_9174940369185036217[268] = 0.0;
   out_9174940369185036217[269] = 0.0;
   out_9174940369185036217[270] = 0.0;
   out_9174940369185036217[271] = 0.0;
   out_9174940369185036217[272] = 0.0;
   out_9174940369185036217[273] = 0.0;
   out_9174940369185036217[274] = 0.0;
   out_9174940369185036217[275] = 0.0;
   out_9174940369185036217[276] = 0.0;
   out_9174940369185036217[277] = 0.0;
   out_9174940369185036217[278] = 0.0;
   out_9174940369185036217[279] = 0.0;
   out_9174940369185036217[280] = 0.0;
   out_9174940369185036217[281] = 0.0;
   out_9174940369185036217[282] = 0.0;
   out_9174940369185036217[283] = 0.0;
   out_9174940369185036217[284] = 0.0;
   out_9174940369185036217[285] = 1.0;
   out_9174940369185036217[286] = 0.0;
   out_9174940369185036217[287] = 0.0;
   out_9174940369185036217[288] = 0.0;
   out_9174940369185036217[289] = 0.0;
   out_9174940369185036217[290] = 0.0;
   out_9174940369185036217[291] = 0.0;
   out_9174940369185036217[292] = 0.0;
   out_9174940369185036217[293] = 0.0;
   out_9174940369185036217[294] = 0.0;
   out_9174940369185036217[295] = 0.0;
   out_9174940369185036217[296] = 0.0;
   out_9174940369185036217[297] = 0.0;
   out_9174940369185036217[298] = 0.0;
   out_9174940369185036217[299] = 0.0;
   out_9174940369185036217[300] = 0.0;
   out_9174940369185036217[301] = 0.0;
   out_9174940369185036217[302] = 0.0;
   out_9174940369185036217[303] = 0.0;
   out_9174940369185036217[304] = 1.0;
   out_9174940369185036217[305] = 0.0;
   out_9174940369185036217[306] = 0.0;
   out_9174940369185036217[307] = 0.0;
   out_9174940369185036217[308] = 0.0;
   out_9174940369185036217[309] = 0.0;
   out_9174940369185036217[310] = 0.0;
   out_9174940369185036217[311] = 0.0;
   out_9174940369185036217[312] = 0.0;
   out_9174940369185036217[313] = 0.0;
   out_9174940369185036217[314] = 0.0;
   out_9174940369185036217[315] = 0.0;
   out_9174940369185036217[316] = 0.0;
   out_9174940369185036217[317] = 0.0;
   out_9174940369185036217[318] = 0.0;
   out_9174940369185036217[319] = 0.0;
   out_9174940369185036217[320] = 0.0;
   out_9174940369185036217[321] = 0.0;
   out_9174940369185036217[322] = 0.0;
   out_9174940369185036217[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4673717053718014348) {
   out_4673717053718014348[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4673717053718014348[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4673717053718014348[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4673717053718014348[3] = dt*state[12] + state[3];
   out_4673717053718014348[4] = dt*state[13] + state[4];
   out_4673717053718014348[5] = dt*state[14] + state[5];
   out_4673717053718014348[6] = state[6];
   out_4673717053718014348[7] = state[7];
   out_4673717053718014348[8] = state[8];
   out_4673717053718014348[9] = state[9];
   out_4673717053718014348[10] = state[10];
   out_4673717053718014348[11] = state[11];
   out_4673717053718014348[12] = state[12];
   out_4673717053718014348[13] = state[13];
   out_4673717053718014348[14] = state[14];
   out_4673717053718014348[15] = state[15];
   out_4673717053718014348[16] = state[16];
   out_4673717053718014348[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7626949901910213403) {
   out_7626949901910213403[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7626949901910213403[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7626949901910213403[2] = 0;
   out_7626949901910213403[3] = 0;
   out_7626949901910213403[4] = 0;
   out_7626949901910213403[5] = 0;
   out_7626949901910213403[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7626949901910213403[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7626949901910213403[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7626949901910213403[9] = 0;
   out_7626949901910213403[10] = 0;
   out_7626949901910213403[11] = 0;
   out_7626949901910213403[12] = 0;
   out_7626949901910213403[13] = 0;
   out_7626949901910213403[14] = 0;
   out_7626949901910213403[15] = 0;
   out_7626949901910213403[16] = 0;
   out_7626949901910213403[17] = 0;
   out_7626949901910213403[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7626949901910213403[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7626949901910213403[20] = 0;
   out_7626949901910213403[21] = 0;
   out_7626949901910213403[22] = 0;
   out_7626949901910213403[23] = 0;
   out_7626949901910213403[24] = 0;
   out_7626949901910213403[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7626949901910213403[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7626949901910213403[27] = 0;
   out_7626949901910213403[28] = 0;
   out_7626949901910213403[29] = 0;
   out_7626949901910213403[30] = 0;
   out_7626949901910213403[31] = 0;
   out_7626949901910213403[32] = 0;
   out_7626949901910213403[33] = 0;
   out_7626949901910213403[34] = 0;
   out_7626949901910213403[35] = 0;
   out_7626949901910213403[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7626949901910213403[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7626949901910213403[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7626949901910213403[39] = 0;
   out_7626949901910213403[40] = 0;
   out_7626949901910213403[41] = 0;
   out_7626949901910213403[42] = 0;
   out_7626949901910213403[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7626949901910213403[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7626949901910213403[45] = 0;
   out_7626949901910213403[46] = 0;
   out_7626949901910213403[47] = 0;
   out_7626949901910213403[48] = 0;
   out_7626949901910213403[49] = 0;
   out_7626949901910213403[50] = 0;
   out_7626949901910213403[51] = 0;
   out_7626949901910213403[52] = 0;
   out_7626949901910213403[53] = 0;
   out_7626949901910213403[54] = 0;
   out_7626949901910213403[55] = 0;
   out_7626949901910213403[56] = 0;
   out_7626949901910213403[57] = 1;
   out_7626949901910213403[58] = 0;
   out_7626949901910213403[59] = 0;
   out_7626949901910213403[60] = 0;
   out_7626949901910213403[61] = 0;
   out_7626949901910213403[62] = 0;
   out_7626949901910213403[63] = 0;
   out_7626949901910213403[64] = 0;
   out_7626949901910213403[65] = 0;
   out_7626949901910213403[66] = dt;
   out_7626949901910213403[67] = 0;
   out_7626949901910213403[68] = 0;
   out_7626949901910213403[69] = 0;
   out_7626949901910213403[70] = 0;
   out_7626949901910213403[71] = 0;
   out_7626949901910213403[72] = 0;
   out_7626949901910213403[73] = 0;
   out_7626949901910213403[74] = 0;
   out_7626949901910213403[75] = 0;
   out_7626949901910213403[76] = 1;
   out_7626949901910213403[77] = 0;
   out_7626949901910213403[78] = 0;
   out_7626949901910213403[79] = 0;
   out_7626949901910213403[80] = 0;
   out_7626949901910213403[81] = 0;
   out_7626949901910213403[82] = 0;
   out_7626949901910213403[83] = 0;
   out_7626949901910213403[84] = 0;
   out_7626949901910213403[85] = dt;
   out_7626949901910213403[86] = 0;
   out_7626949901910213403[87] = 0;
   out_7626949901910213403[88] = 0;
   out_7626949901910213403[89] = 0;
   out_7626949901910213403[90] = 0;
   out_7626949901910213403[91] = 0;
   out_7626949901910213403[92] = 0;
   out_7626949901910213403[93] = 0;
   out_7626949901910213403[94] = 0;
   out_7626949901910213403[95] = 1;
   out_7626949901910213403[96] = 0;
   out_7626949901910213403[97] = 0;
   out_7626949901910213403[98] = 0;
   out_7626949901910213403[99] = 0;
   out_7626949901910213403[100] = 0;
   out_7626949901910213403[101] = 0;
   out_7626949901910213403[102] = 0;
   out_7626949901910213403[103] = 0;
   out_7626949901910213403[104] = dt;
   out_7626949901910213403[105] = 0;
   out_7626949901910213403[106] = 0;
   out_7626949901910213403[107] = 0;
   out_7626949901910213403[108] = 0;
   out_7626949901910213403[109] = 0;
   out_7626949901910213403[110] = 0;
   out_7626949901910213403[111] = 0;
   out_7626949901910213403[112] = 0;
   out_7626949901910213403[113] = 0;
   out_7626949901910213403[114] = 1;
   out_7626949901910213403[115] = 0;
   out_7626949901910213403[116] = 0;
   out_7626949901910213403[117] = 0;
   out_7626949901910213403[118] = 0;
   out_7626949901910213403[119] = 0;
   out_7626949901910213403[120] = 0;
   out_7626949901910213403[121] = 0;
   out_7626949901910213403[122] = 0;
   out_7626949901910213403[123] = 0;
   out_7626949901910213403[124] = 0;
   out_7626949901910213403[125] = 0;
   out_7626949901910213403[126] = 0;
   out_7626949901910213403[127] = 0;
   out_7626949901910213403[128] = 0;
   out_7626949901910213403[129] = 0;
   out_7626949901910213403[130] = 0;
   out_7626949901910213403[131] = 0;
   out_7626949901910213403[132] = 0;
   out_7626949901910213403[133] = 1;
   out_7626949901910213403[134] = 0;
   out_7626949901910213403[135] = 0;
   out_7626949901910213403[136] = 0;
   out_7626949901910213403[137] = 0;
   out_7626949901910213403[138] = 0;
   out_7626949901910213403[139] = 0;
   out_7626949901910213403[140] = 0;
   out_7626949901910213403[141] = 0;
   out_7626949901910213403[142] = 0;
   out_7626949901910213403[143] = 0;
   out_7626949901910213403[144] = 0;
   out_7626949901910213403[145] = 0;
   out_7626949901910213403[146] = 0;
   out_7626949901910213403[147] = 0;
   out_7626949901910213403[148] = 0;
   out_7626949901910213403[149] = 0;
   out_7626949901910213403[150] = 0;
   out_7626949901910213403[151] = 0;
   out_7626949901910213403[152] = 1;
   out_7626949901910213403[153] = 0;
   out_7626949901910213403[154] = 0;
   out_7626949901910213403[155] = 0;
   out_7626949901910213403[156] = 0;
   out_7626949901910213403[157] = 0;
   out_7626949901910213403[158] = 0;
   out_7626949901910213403[159] = 0;
   out_7626949901910213403[160] = 0;
   out_7626949901910213403[161] = 0;
   out_7626949901910213403[162] = 0;
   out_7626949901910213403[163] = 0;
   out_7626949901910213403[164] = 0;
   out_7626949901910213403[165] = 0;
   out_7626949901910213403[166] = 0;
   out_7626949901910213403[167] = 0;
   out_7626949901910213403[168] = 0;
   out_7626949901910213403[169] = 0;
   out_7626949901910213403[170] = 0;
   out_7626949901910213403[171] = 1;
   out_7626949901910213403[172] = 0;
   out_7626949901910213403[173] = 0;
   out_7626949901910213403[174] = 0;
   out_7626949901910213403[175] = 0;
   out_7626949901910213403[176] = 0;
   out_7626949901910213403[177] = 0;
   out_7626949901910213403[178] = 0;
   out_7626949901910213403[179] = 0;
   out_7626949901910213403[180] = 0;
   out_7626949901910213403[181] = 0;
   out_7626949901910213403[182] = 0;
   out_7626949901910213403[183] = 0;
   out_7626949901910213403[184] = 0;
   out_7626949901910213403[185] = 0;
   out_7626949901910213403[186] = 0;
   out_7626949901910213403[187] = 0;
   out_7626949901910213403[188] = 0;
   out_7626949901910213403[189] = 0;
   out_7626949901910213403[190] = 1;
   out_7626949901910213403[191] = 0;
   out_7626949901910213403[192] = 0;
   out_7626949901910213403[193] = 0;
   out_7626949901910213403[194] = 0;
   out_7626949901910213403[195] = 0;
   out_7626949901910213403[196] = 0;
   out_7626949901910213403[197] = 0;
   out_7626949901910213403[198] = 0;
   out_7626949901910213403[199] = 0;
   out_7626949901910213403[200] = 0;
   out_7626949901910213403[201] = 0;
   out_7626949901910213403[202] = 0;
   out_7626949901910213403[203] = 0;
   out_7626949901910213403[204] = 0;
   out_7626949901910213403[205] = 0;
   out_7626949901910213403[206] = 0;
   out_7626949901910213403[207] = 0;
   out_7626949901910213403[208] = 0;
   out_7626949901910213403[209] = 1;
   out_7626949901910213403[210] = 0;
   out_7626949901910213403[211] = 0;
   out_7626949901910213403[212] = 0;
   out_7626949901910213403[213] = 0;
   out_7626949901910213403[214] = 0;
   out_7626949901910213403[215] = 0;
   out_7626949901910213403[216] = 0;
   out_7626949901910213403[217] = 0;
   out_7626949901910213403[218] = 0;
   out_7626949901910213403[219] = 0;
   out_7626949901910213403[220] = 0;
   out_7626949901910213403[221] = 0;
   out_7626949901910213403[222] = 0;
   out_7626949901910213403[223] = 0;
   out_7626949901910213403[224] = 0;
   out_7626949901910213403[225] = 0;
   out_7626949901910213403[226] = 0;
   out_7626949901910213403[227] = 0;
   out_7626949901910213403[228] = 1;
   out_7626949901910213403[229] = 0;
   out_7626949901910213403[230] = 0;
   out_7626949901910213403[231] = 0;
   out_7626949901910213403[232] = 0;
   out_7626949901910213403[233] = 0;
   out_7626949901910213403[234] = 0;
   out_7626949901910213403[235] = 0;
   out_7626949901910213403[236] = 0;
   out_7626949901910213403[237] = 0;
   out_7626949901910213403[238] = 0;
   out_7626949901910213403[239] = 0;
   out_7626949901910213403[240] = 0;
   out_7626949901910213403[241] = 0;
   out_7626949901910213403[242] = 0;
   out_7626949901910213403[243] = 0;
   out_7626949901910213403[244] = 0;
   out_7626949901910213403[245] = 0;
   out_7626949901910213403[246] = 0;
   out_7626949901910213403[247] = 1;
   out_7626949901910213403[248] = 0;
   out_7626949901910213403[249] = 0;
   out_7626949901910213403[250] = 0;
   out_7626949901910213403[251] = 0;
   out_7626949901910213403[252] = 0;
   out_7626949901910213403[253] = 0;
   out_7626949901910213403[254] = 0;
   out_7626949901910213403[255] = 0;
   out_7626949901910213403[256] = 0;
   out_7626949901910213403[257] = 0;
   out_7626949901910213403[258] = 0;
   out_7626949901910213403[259] = 0;
   out_7626949901910213403[260] = 0;
   out_7626949901910213403[261] = 0;
   out_7626949901910213403[262] = 0;
   out_7626949901910213403[263] = 0;
   out_7626949901910213403[264] = 0;
   out_7626949901910213403[265] = 0;
   out_7626949901910213403[266] = 1;
   out_7626949901910213403[267] = 0;
   out_7626949901910213403[268] = 0;
   out_7626949901910213403[269] = 0;
   out_7626949901910213403[270] = 0;
   out_7626949901910213403[271] = 0;
   out_7626949901910213403[272] = 0;
   out_7626949901910213403[273] = 0;
   out_7626949901910213403[274] = 0;
   out_7626949901910213403[275] = 0;
   out_7626949901910213403[276] = 0;
   out_7626949901910213403[277] = 0;
   out_7626949901910213403[278] = 0;
   out_7626949901910213403[279] = 0;
   out_7626949901910213403[280] = 0;
   out_7626949901910213403[281] = 0;
   out_7626949901910213403[282] = 0;
   out_7626949901910213403[283] = 0;
   out_7626949901910213403[284] = 0;
   out_7626949901910213403[285] = 1;
   out_7626949901910213403[286] = 0;
   out_7626949901910213403[287] = 0;
   out_7626949901910213403[288] = 0;
   out_7626949901910213403[289] = 0;
   out_7626949901910213403[290] = 0;
   out_7626949901910213403[291] = 0;
   out_7626949901910213403[292] = 0;
   out_7626949901910213403[293] = 0;
   out_7626949901910213403[294] = 0;
   out_7626949901910213403[295] = 0;
   out_7626949901910213403[296] = 0;
   out_7626949901910213403[297] = 0;
   out_7626949901910213403[298] = 0;
   out_7626949901910213403[299] = 0;
   out_7626949901910213403[300] = 0;
   out_7626949901910213403[301] = 0;
   out_7626949901910213403[302] = 0;
   out_7626949901910213403[303] = 0;
   out_7626949901910213403[304] = 1;
   out_7626949901910213403[305] = 0;
   out_7626949901910213403[306] = 0;
   out_7626949901910213403[307] = 0;
   out_7626949901910213403[308] = 0;
   out_7626949901910213403[309] = 0;
   out_7626949901910213403[310] = 0;
   out_7626949901910213403[311] = 0;
   out_7626949901910213403[312] = 0;
   out_7626949901910213403[313] = 0;
   out_7626949901910213403[314] = 0;
   out_7626949901910213403[315] = 0;
   out_7626949901910213403[316] = 0;
   out_7626949901910213403[317] = 0;
   out_7626949901910213403[318] = 0;
   out_7626949901910213403[319] = 0;
   out_7626949901910213403[320] = 0;
   out_7626949901910213403[321] = 0;
   out_7626949901910213403[322] = 0;
   out_7626949901910213403[323] = 1;
}
void h_4(double *state, double *unused, double *out_2637904353676577) {
   out_2637904353676577[0] = state[6] + state[9];
   out_2637904353676577[1] = state[7] + state[10];
   out_2637904353676577[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3423721897772556678) {
   out_3423721897772556678[0] = 0;
   out_3423721897772556678[1] = 0;
   out_3423721897772556678[2] = 0;
   out_3423721897772556678[3] = 0;
   out_3423721897772556678[4] = 0;
   out_3423721897772556678[5] = 0;
   out_3423721897772556678[6] = 1;
   out_3423721897772556678[7] = 0;
   out_3423721897772556678[8] = 0;
   out_3423721897772556678[9] = 1;
   out_3423721897772556678[10] = 0;
   out_3423721897772556678[11] = 0;
   out_3423721897772556678[12] = 0;
   out_3423721897772556678[13] = 0;
   out_3423721897772556678[14] = 0;
   out_3423721897772556678[15] = 0;
   out_3423721897772556678[16] = 0;
   out_3423721897772556678[17] = 0;
   out_3423721897772556678[18] = 0;
   out_3423721897772556678[19] = 0;
   out_3423721897772556678[20] = 0;
   out_3423721897772556678[21] = 0;
   out_3423721897772556678[22] = 0;
   out_3423721897772556678[23] = 0;
   out_3423721897772556678[24] = 0;
   out_3423721897772556678[25] = 1;
   out_3423721897772556678[26] = 0;
   out_3423721897772556678[27] = 0;
   out_3423721897772556678[28] = 1;
   out_3423721897772556678[29] = 0;
   out_3423721897772556678[30] = 0;
   out_3423721897772556678[31] = 0;
   out_3423721897772556678[32] = 0;
   out_3423721897772556678[33] = 0;
   out_3423721897772556678[34] = 0;
   out_3423721897772556678[35] = 0;
   out_3423721897772556678[36] = 0;
   out_3423721897772556678[37] = 0;
   out_3423721897772556678[38] = 0;
   out_3423721897772556678[39] = 0;
   out_3423721897772556678[40] = 0;
   out_3423721897772556678[41] = 0;
   out_3423721897772556678[42] = 0;
   out_3423721897772556678[43] = 0;
   out_3423721897772556678[44] = 1;
   out_3423721897772556678[45] = 0;
   out_3423721897772556678[46] = 0;
   out_3423721897772556678[47] = 1;
   out_3423721897772556678[48] = 0;
   out_3423721897772556678[49] = 0;
   out_3423721897772556678[50] = 0;
   out_3423721897772556678[51] = 0;
   out_3423721897772556678[52] = 0;
   out_3423721897772556678[53] = 0;
}
void h_10(double *state, double *unused, double *out_2208932603856339349) {
   out_2208932603856339349[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2208932603856339349[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2208932603856339349[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_1086050679309335415) {
   out_1086050679309335415[0] = 0;
   out_1086050679309335415[1] = 9.8100000000000005*cos(state[1]);
   out_1086050679309335415[2] = 0;
   out_1086050679309335415[3] = 0;
   out_1086050679309335415[4] = -state[8];
   out_1086050679309335415[5] = state[7];
   out_1086050679309335415[6] = 0;
   out_1086050679309335415[7] = state[5];
   out_1086050679309335415[8] = -state[4];
   out_1086050679309335415[9] = 0;
   out_1086050679309335415[10] = 0;
   out_1086050679309335415[11] = 0;
   out_1086050679309335415[12] = 1;
   out_1086050679309335415[13] = 0;
   out_1086050679309335415[14] = 0;
   out_1086050679309335415[15] = 1;
   out_1086050679309335415[16] = 0;
   out_1086050679309335415[17] = 0;
   out_1086050679309335415[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_1086050679309335415[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_1086050679309335415[20] = 0;
   out_1086050679309335415[21] = state[8];
   out_1086050679309335415[22] = 0;
   out_1086050679309335415[23] = -state[6];
   out_1086050679309335415[24] = -state[5];
   out_1086050679309335415[25] = 0;
   out_1086050679309335415[26] = state[3];
   out_1086050679309335415[27] = 0;
   out_1086050679309335415[28] = 0;
   out_1086050679309335415[29] = 0;
   out_1086050679309335415[30] = 0;
   out_1086050679309335415[31] = 1;
   out_1086050679309335415[32] = 0;
   out_1086050679309335415[33] = 0;
   out_1086050679309335415[34] = 1;
   out_1086050679309335415[35] = 0;
   out_1086050679309335415[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_1086050679309335415[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_1086050679309335415[38] = 0;
   out_1086050679309335415[39] = -state[7];
   out_1086050679309335415[40] = state[6];
   out_1086050679309335415[41] = 0;
   out_1086050679309335415[42] = state[4];
   out_1086050679309335415[43] = -state[3];
   out_1086050679309335415[44] = 0;
   out_1086050679309335415[45] = 0;
   out_1086050679309335415[46] = 0;
   out_1086050679309335415[47] = 0;
   out_1086050679309335415[48] = 0;
   out_1086050679309335415[49] = 0;
   out_1086050679309335415[50] = 1;
   out_1086050679309335415[51] = 0;
   out_1086050679309335415[52] = 0;
   out_1086050679309335415[53] = 1;
}
void h_13(double *state, double *unused, double *out_8307148822937221148) {
   out_8307148822937221148[0] = state[3];
   out_8307148822937221148[1] = state[4];
   out_8307148822937221148[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6635995723104889479) {
   out_6635995723104889479[0] = 0;
   out_6635995723104889479[1] = 0;
   out_6635995723104889479[2] = 0;
   out_6635995723104889479[3] = 1;
   out_6635995723104889479[4] = 0;
   out_6635995723104889479[5] = 0;
   out_6635995723104889479[6] = 0;
   out_6635995723104889479[7] = 0;
   out_6635995723104889479[8] = 0;
   out_6635995723104889479[9] = 0;
   out_6635995723104889479[10] = 0;
   out_6635995723104889479[11] = 0;
   out_6635995723104889479[12] = 0;
   out_6635995723104889479[13] = 0;
   out_6635995723104889479[14] = 0;
   out_6635995723104889479[15] = 0;
   out_6635995723104889479[16] = 0;
   out_6635995723104889479[17] = 0;
   out_6635995723104889479[18] = 0;
   out_6635995723104889479[19] = 0;
   out_6635995723104889479[20] = 0;
   out_6635995723104889479[21] = 0;
   out_6635995723104889479[22] = 1;
   out_6635995723104889479[23] = 0;
   out_6635995723104889479[24] = 0;
   out_6635995723104889479[25] = 0;
   out_6635995723104889479[26] = 0;
   out_6635995723104889479[27] = 0;
   out_6635995723104889479[28] = 0;
   out_6635995723104889479[29] = 0;
   out_6635995723104889479[30] = 0;
   out_6635995723104889479[31] = 0;
   out_6635995723104889479[32] = 0;
   out_6635995723104889479[33] = 0;
   out_6635995723104889479[34] = 0;
   out_6635995723104889479[35] = 0;
   out_6635995723104889479[36] = 0;
   out_6635995723104889479[37] = 0;
   out_6635995723104889479[38] = 0;
   out_6635995723104889479[39] = 0;
   out_6635995723104889479[40] = 0;
   out_6635995723104889479[41] = 1;
   out_6635995723104889479[42] = 0;
   out_6635995723104889479[43] = 0;
   out_6635995723104889479[44] = 0;
   out_6635995723104889479[45] = 0;
   out_6635995723104889479[46] = 0;
   out_6635995723104889479[47] = 0;
   out_6635995723104889479[48] = 0;
   out_6635995723104889479[49] = 0;
   out_6635995723104889479[50] = 0;
   out_6635995723104889479[51] = 0;
   out_6635995723104889479[52] = 0;
   out_6635995723104889479[53] = 0;
}
void h_14(double *state, double *unused, double *out_81297754970292080) {
   out_81297754970292080[0] = state[6];
   out_81297754970292080[1] = state[7];
   out_81297754970292080[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7386962754112041207) {
   out_7386962754112041207[0] = 0;
   out_7386962754112041207[1] = 0;
   out_7386962754112041207[2] = 0;
   out_7386962754112041207[3] = 0;
   out_7386962754112041207[4] = 0;
   out_7386962754112041207[5] = 0;
   out_7386962754112041207[6] = 1;
   out_7386962754112041207[7] = 0;
   out_7386962754112041207[8] = 0;
   out_7386962754112041207[9] = 0;
   out_7386962754112041207[10] = 0;
   out_7386962754112041207[11] = 0;
   out_7386962754112041207[12] = 0;
   out_7386962754112041207[13] = 0;
   out_7386962754112041207[14] = 0;
   out_7386962754112041207[15] = 0;
   out_7386962754112041207[16] = 0;
   out_7386962754112041207[17] = 0;
   out_7386962754112041207[18] = 0;
   out_7386962754112041207[19] = 0;
   out_7386962754112041207[20] = 0;
   out_7386962754112041207[21] = 0;
   out_7386962754112041207[22] = 0;
   out_7386962754112041207[23] = 0;
   out_7386962754112041207[24] = 0;
   out_7386962754112041207[25] = 1;
   out_7386962754112041207[26] = 0;
   out_7386962754112041207[27] = 0;
   out_7386962754112041207[28] = 0;
   out_7386962754112041207[29] = 0;
   out_7386962754112041207[30] = 0;
   out_7386962754112041207[31] = 0;
   out_7386962754112041207[32] = 0;
   out_7386962754112041207[33] = 0;
   out_7386962754112041207[34] = 0;
   out_7386962754112041207[35] = 0;
   out_7386962754112041207[36] = 0;
   out_7386962754112041207[37] = 0;
   out_7386962754112041207[38] = 0;
   out_7386962754112041207[39] = 0;
   out_7386962754112041207[40] = 0;
   out_7386962754112041207[41] = 0;
   out_7386962754112041207[42] = 0;
   out_7386962754112041207[43] = 0;
   out_7386962754112041207[44] = 1;
   out_7386962754112041207[45] = 0;
   out_7386962754112041207[46] = 0;
   out_7386962754112041207[47] = 0;
   out_7386962754112041207[48] = 0;
   out_7386962754112041207[49] = 0;
   out_7386962754112041207[50] = 0;
   out_7386962754112041207[51] = 0;
   out_7386962754112041207[52] = 0;
   out_7386962754112041207[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5566842885647767369) {
  err_fun(nom_x, delta_x, out_5566842885647767369);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7605915063363770360) {
  inv_err_fun(nom_x, true_x, out_7605915063363770360);
}
void pose_H_mod_fun(double *state, double *out_9174940369185036217) {
  H_mod_fun(state, out_9174940369185036217);
}
void pose_f_fun(double *state, double dt, double *out_4673717053718014348) {
  f_fun(state,  dt, out_4673717053718014348);
}
void pose_F_fun(double *state, double dt, double *out_7626949901910213403) {
  F_fun(state,  dt, out_7626949901910213403);
}
void pose_h_4(double *state, double *unused, double *out_2637904353676577) {
  h_4(state, unused, out_2637904353676577);
}
void pose_H_4(double *state, double *unused, double *out_3423721897772556678) {
  H_4(state, unused, out_3423721897772556678);
}
void pose_h_10(double *state, double *unused, double *out_2208932603856339349) {
  h_10(state, unused, out_2208932603856339349);
}
void pose_H_10(double *state, double *unused, double *out_1086050679309335415) {
  H_10(state, unused, out_1086050679309335415);
}
void pose_h_13(double *state, double *unused, double *out_8307148822937221148) {
  h_13(state, unused, out_8307148822937221148);
}
void pose_H_13(double *state, double *unused, double *out_6635995723104889479) {
  H_13(state, unused, out_6635995723104889479);
}
void pose_h_14(double *state, double *unused, double *out_81297754970292080) {
  h_14(state, unused, out_81297754970292080);
}
void pose_H_14(double *state, double *unused, double *out_7386962754112041207) {
  H_14(state, unused, out_7386962754112041207);
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
