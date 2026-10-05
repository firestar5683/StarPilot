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
void err_fun(double *nom_x, double *delta_x, double *out_5436717349763929250) {
   out_5436717349763929250[0] = delta_x[0] + nom_x[0];
   out_5436717349763929250[1] = delta_x[1] + nom_x[1];
   out_5436717349763929250[2] = delta_x[2] + nom_x[2];
   out_5436717349763929250[3] = delta_x[3] + nom_x[3];
   out_5436717349763929250[4] = delta_x[4] + nom_x[4];
   out_5436717349763929250[5] = delta_x[5] + nom_x[5];
   out_5436717349763929250[6] = delta_x[6] + nom_x[6];
   out_5436717349763929250[7] = delta_x[7] + nom_x[7];
   out_5436717349763929250[8] = delta_x[8] + nom_x[8];
   out_5436717349763929250[9] = delta_x[9] + nom_x[9];
   out_5436717349763929250[10] = delta_x[10] + nom_x[10];
   out_5436717349763929250[11] = delta_x[11] + nom_x[11];
   out_5436717349763929250[12] = delta_x[12] + nom_x[12];
   out_5436717349763929250[13] = delta_x[13] + nom_x[13];
   out_5436717349763929250[14] = delta_x[14] + nom_x[14];
   out_5436717349763929250[15] = delta_x[15] + nom_x[15];
   out_5436717349763929250[16] = delta_x[16] + nom_x[16];
   out_5436717349763929250[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2267989734965085487) {
   out_2267989734965085487[0] = -nom_x[0] + true_x[0];
   out_2267989734965085487[1] = -nom_x[1] + true_x[1];
   out_2267989734965085487[2] = -nom_x[2] + true_x[2];
   out_2267989734965085487[3] = -nom_x[3] + true_x[3];
   out_2267989734965085487[4] = -nom_x[4] + true_x[4];
   out_2267989734965085487[5] = -nom_x[5] + true_x[5];
   out_2267989734965085487[6] = -nom_x[6] + true_x[6];
   out_2267989734965085487[7] = -nom_x[7] + true_x[7];
   out_2267989734965085487[8] = -nom_x[8] + true_x[8];
   out_2267989734965085487[9] = -nom_x[9] + true_x[9];
   out_2267989734965085487[10] = -nom_x[10] + true_x[10];
   out_2267989734965085487[11] = -nom_x[11] + true_x[11];
   out_2267989734965085487[12] = -nom_x[12] + true_x[12];
   out_2267989734965085487[13] = -nom_x[13] + true_x[13];
   out_2267989734965085487[14] = -nom_x[14] + true_x[14];
   out_2267989734965085487[15] = -nom_x[15] + true_x[15];
   out_2267989734965085487[16] = -nom_x[16] + true_x[16];
   out_2267989734965085487[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7252406541217060893) {
   out_7252406541217060893[0] = 1.0;
   out_7252406541217060893[1] = 0.0;
   out_7252406541217060893[2] = 0.0;
   out_7252406541217060893[3] = 0.0;
   out_7252406541217060893[4] = 0.0;
   out_7252406541217060893[5] = 0.0;
   out_7252406541217060893[6] = 0.0;
   out_7252406541217060893[7] = 0.0;
   out_7252406541217060893[8] = 0.0;
   out_7252406541217060893[9] = 0.0;
   out_7252406541217060893[10] = 0.0;
   out_7252406541217060893[11] = 0.0;
   out_7252406541217060893[12] = 0.0;
   out_7252406541217060893[13] = 0.0;
   out_7252406541217060893[14] = 0.0;
   out_7252406541217060893[15] = 0.0;
   out_7252406541217060893[16] = 0.0;
   out_7252406541217060893[17] = 0.0;
   out_7252406541217060893[18] = 0.0;
   out_7252406541217060893[19] = 1.0;
   out_7252406541217060893[20] = 0.0;
   out_7252406541217060893[21] = 0.0;
   out_7252406541217060893[22] = 0.0;
   out_7252406541217060893[23] = 0.0;
   out_7252406541217060893[24] = 0.0;
   out_7252406541217060893[25] = 0.0;
   out_7252406541217060893[26] = 0.0;
   out_7252406541217060893[27] = 0.0;
   out_7252406541217060893[28] = 0.0;
   out_7252406541217060893[29] = 0.0;
   out_7252406541217060893[30] = 0.0;
   out_7252406541217060893[31] = 0.0;
   out_7252406541217060893[32] = 0.0;
   out_7252406541217060893[33] = 0.0;
   out_7252406541217060893[34] = 0.0;
   out_7252406541217060893[35] = 0.0;
   out_7252406541217060893[36] = 0.0;
   out_7252406541217060893[37] = 0.0;
   out_7252406541217060893[38] = 1.0;
   out_7252406541217060893[39] = 0.0;
   out_7252406541217060893[40] = 0.0;
   out_7252406541217060893[41] = 0.0;
   out_7252406541217060893[42] = 0.0;
   out_7252406541217060893[43] = 0.0;
   out_7252406541217060893[44] = 0.0;
   out_7252406541217060893[45] = 0.0;
   out_7252406541217060893[46] = 0.0;
   out_7252406541217060893[47] = 0.0;
   out_7252406541217060893[48] = 0.0;
   out_7252406541217060893[49] = 0.0;
   out_7252406541217060893[50] = 0.0;
   out_7252406541217060893[51] = 0.0;
   out_7252406541217060893[52] = 0.0;
   out_7252406541217060893[53] = 0.0;
   out_7252406541217060893[54] = 0.0;
   out_7252406541217060893[55] = 0.0;
   out_7252406541217060893[56] = 0.0;
   out_7252406541217060893[57] = 1.0;
   out_7252406541217060893[58] = 0.0;
   out_7252406541217060893[59] = 0.0;
   out_7252406541217060893[60] = 0.0;
   out_7252406541217060893[61] = 0.0;
   out_7252406541217060893[62] = 0.0;
   out_7252406541217060893[63] = 0.0;
   out_7252406541217060893[64] = 0.0;
   out_7252406541217060893[65] = 0.0;
   out_7252406541217060893[66] = 0.0;
   out_7252406541217060893[67] = 0.0;
   out_7252406541217060893[68] = 0.0;
   out_7252406541217060893[69] = 0.0;
   out_7252406541217060893[70] = 0.0;
   out_7252406541217060893[71] = 0.0;
   out_7252406541217060893[72] = 0.0;
   out_7252406541217060893[73] = 0.0;
   out_7252406541217060893[74] = 0.0;
   out_7252406541217060893[75] = 0.0;
   out_7252406541217060893[76] = 1.0;
   out_7252406541217060893[77] = 0.0;
   out_7252406541217060893[78] = 0.0;
   out_7252406541217060893[79] = 0.0;
   out_7252406541217060893[80] = 0.0;
   out_7252406541217060893[81] = 0.0;
   out_7252406541217060893[82] = 0.0;
   out_7252406541217060893[83] = 0.0;
   out_7252406541217060893[84] = 0.0;
   out_7252406541217060893[85] = 0.0;
   out_7252406541217060893[86] = 0.0;
   out_7252406541217060893[87] = 0.0;
   out_7252406541217060893[88] = 0.0;
   out_7252406541217060893[89] = 0.0;
   out_7252406541217060893[90] = 0.0;
   out_7252406541217060893[91] = 0.0;
   out_7252406541217060893[92] = 0.0;
   out_7252406541217060893[93] = 0.0;
   out_7252406541217060893[94] = 0.0;
   out_7252406541217060893[95] = 1.0;
   out_7252406541217060893[96] = 0.0;
   out_7252406541217060893[97] = 0.0;
   out_7252406541217060893[98] = 0.0;
   out_7252406541217060893[99] = 0.0;
   out_7252406541217060893[100] = 0.0;
   out_7252406541217060893[101] = 0.0;
   out_7252406541217060893[102] = 0.0;
   out_7252406541217060893[103] = 0.0;
   out_7252406541217060893[104] = 0.0;
   out_7252406541217060893[105] = 0.0;
   out_7252406541217060893[106] = 0.0;
   out_7252406541217060893[107] = 0.0;
   out_7252406541217060893[108] = 0.0;
   out_7252406541217060893[109] = 0.0;
   out_7252406541217060893[110] = 0.0;
   out_7252406541217060893[111] = 0.0;
   out_7252406541217060893[112] = 0.0;
   out_7252406541217060893[113] = 0.0;
   out_7252406541217060893[114] = 1.0;
   out_7252406541217060893[115] = 0.0;
   out_7252406541217060893[116] = 0.0;
   out_7252406541217060893[117] = 0.0;
   out_7252406541217060893[118] = 0.0;
   out_7252406541217060893[119] = 0.0;
   out_7252406541217060893[120] = 0.0;
   out_7252406541217060893[121] = 0.0;
   out_7252406541217060893[122] = 0.0;
   out_7252406541217060893[123] = 0.0;
   out_7252406541217060893[124] = 0.0;
   out_7252406541217060893[125] = 0.0;
   out_7252406541217060893[126] = 0.0;
   out_7252406541217060893[127] = 0.0;
   out_7252406541217060893[128] = 0.0;
   out_7252406541217060893[129] = 0.0;
   out_7252406541217060893[130] = 0.0;
   out_7252406541217060893[131] = 0.0;
   out_7252406541217060893[132] = 0.0;
   out_7252406541217060893[133] = 1.0;
   out_7252406541217060893[134] = 0.0;
   out_7252406541217060893[135] = 0.0;
   out_7252406541217060893[136] = 0.0;
   out_7252406541217060893[137] = 0.0;
   out_7252406541217060893[138] = 0.0;
   out_7252406541217060893[139] = 0.0;
   out_7252406541217060893[140] = 0.0;
   out_7252406541217060893[141] = 0.0;
   out_7252406541217060893[142] = 0.0;
   out_7252406541217060893[143] = 0.0;
   out_7252406541217060893[144] = 0.0;
   out_7252406541217060893[145] = 0.0;
   out_7252406541217060893[146] = 0.0;
   out_7252406541217060893[147] = 0.0;
   out_7252406541217060893[148] = 0.0;
   out_7252406541217060893[149] = 0.0;
   out_7252406541217060893[150] = 0.0;
   out_7252406541217060893[151] = 0.0;
   out_7252406541217060893[152] = 1.0;
   out_7252406541217060893[153] = 0.0;
   out_7252406541217060893[154] = 0.0;
   out_7252406541217060893[155] = 0.0;
   out_7252406541217060893[156] = 0.0;
   out_7252406541217060893[157] = 0.0;
   out_7252406541217060893[158] = 0.0;
   out_7252406541217060893[159] = 0.0;
   out_7252406541217060893[160] = 0.0;
   out_7252406541217060893[161] = 0.0;
   out_7252406541217060893[162] = 0.0;
   out_7252406541217060893[163] = 0.0;
   out_7252406541217060893[164] = 0.0;
   out_7252406541217060893[165] = 0.0;
   out_7252406541217060893[166] = 0.0;
   out_7252406541217060893[167] = 0.0;
   out_7252406541217060893[168] = 0.0;
   out_7252406541217060893[169] = 0.0;
   out_7252406541217060893[170] = 0.0;
   out_7252406541217060893[171] = 1.0;
   out_7252406541217060893[172] = 0.0;
   out_7252406541217060893[173] = 0.0;
   out_7252406541217060893[174] = 0.0;
   out_7252406541217060893[175] = 0.0;
   out_7252406541217060893[176] = 0.0;
   out_7252406541217060893[177] = 0.0;
   out_7252406541217060893[178] = 0.0;
   out_7252406541217060893[179] = 0.0;
   out_7252406541217060893[180] = 0.0;
   out_7252406541217060893[181] = 0.0;
   out_7252406541217060893[182] = 0.0;
   out_7252406541217060893[183] = 0.0;
   out_7252406541217060893[184] = 0.0;
   out_7252406541217060893[185] = 0.0;
   out_7252406541217060893[186] = 0.0;
   out_7252406541217060893[187] = 0.0;
   out_7252406541217060893[188] = 0.0;
   out_7252406541217060893[189] = 0.0;
   out_7252406541217060893[190] = 1.0;
   out_7252406541217060893[191] = 0.0;
   out_7252406541217060893[192] = 0.0;
   out_7252406541217060893[193] = 0.0;
   out_7252406541217060893[194] = 0.0;
   out_7252406541217060893[195] = 0.0;
   out_7252406541217060893[196] = 0.0;
   out_7252406541217060893[197] = 0.0;
   out_7252406541217060893[198] = 0.0;
   out_7252406541217060893[199] = 0.0;
   out_7252406541217060893[200] = 0.0;
   out_7252406541217060893[201] = 0.0;
   out_7252406541217060893[202] = 0.0;
   out_7252406541217060893[203] = 0.0;
   out_7252406541217060893[204] = 0.0;
   out_7252406541217060893[205] = 0.0;
   out_7252406541217060893[206] = 0.0;
   out_7252406541217060893[207] = 0.0;
   out_7252406541217060893[208] = 0.0;
   out_7252406541217060893[209] = 1.0;
   out_7252406541217060893[210] = 0.0;
   out_7252406541217060893[211] = 0.0;
   out_7252406541217060893[212] = 0.0;
   out_7252406541217060893[213] = 0.0;
   out_7252406541217060893[214] = 0.0;
   out_7252406541217060893[215] = 0.0;
   out_7252406541217060893[216] = 0.0;
   out_7252406541217060893[217] = 0.0;
   out_7252406541217060893[218] = 0.0;
   out_7252406541217060893[219] = 0.0;
   out_7252406541217060893[220] = 0.0;
   out_7252406541217060893[221] = 0.0;
   out_7252406541217060893[222] = 0.0;
   out_7252406541217060893[223] = 0.0;
   out_7252406541217060893[224] = 0.0;
   out_7252406541217060893[225] = 0.0;
   out_7252406541217060893[226] = 0.0;
   out_7252406541217060893[227] = 0.0;
   out_7252406541217060893[228] = 1.0;
   out_7252406541217060893[229] = 0.0;
   out_7252406541217060893[230] = 0.0;
   out_7252406541217060893[231] = 0.0;
   out_7252406541217060893[232] = 0.0;
   out_7252406541217060893[233] = 0.0;
   out_7252406541217060893[234] = 0.0;
   out_7252406541217060893[235] = 0.0;
   out_7252406541217060893[236] = 0.0;
   out_7252406541217060893[237] = 0.0;
   out_7252406541217060893[238] = 0.0;
   out_7252406541217060893[239] = 0.0;
   out_7252406541217060893[240] = 0.0;
   out_7252406541217060893[241] = 0.0;
   out_7252406541217060893[242] = 0.0;
   out_7252406541217060893[243] = 0.0;
   out_7252406541217060893[244] = 0.0;
   out_7252406541217060893[245] = 0.0;
   out_7252406541217060893[246] = 0.0;
   out_7252406541217060893[247] = 1.0;
   out_7252406541217060893[248] = 0.0;
   out_7252406541217060893[249] = 0.0;
   out_7252406541217060893[250] = 0.0;
   out_7252406541217060893[251] = 0.0;
   out_7252406541217060893[252] = 0.0;
   out_7252406541217060893[253] = 0.0;
   out_7252406541217060893[254] = 0.0;
   out_7252406541217060893[255] = 0.0;
   out_7252406541217060893[256] = 0.0;
   out_7252406541217060893[257] = 0.0;
   out_7252406541217060893[258] = 0.0;
   out_7252406541217060893[259] = 0.0;
   out_7252406541217060893[260] = 0.0;
   out_7252406541217060893[261] = 0.0;
   out_7252406541217060893[262] = 0.0;
   out_7252406541217060893[263] = 0.0;
   out_7252406541217060893[264] = 0.0;
   out_7252406541217060893[265] = 0.0;
   out_7252406541217060893[266] = 1.0;
   out_7252406541217060893[267] = 0.0;
   out_7252406541217060893[268] = 0.0;
   out_7252406541217060893[269] = 0.0;
   out_7252406541217060893[270] = 0.0;
   out_7252406541217060893[271] = 0.0;
   out_7252406541217060893[272] = 0.0;
   out_7252406541217060893[273] = 0.0;
   out_7252406541217060893[274] = 0.0;
   out_7252406541217060893[275] = 0.0;
   out_7252406541217060893[276] = 0.0;
   out_7252406541217060893[277] = 0.0;
   out_7252406541217060893[278] = 0.0;
   out_7252406541217060893[279] = 0.0;
   out_7252406541217060893[280] = 0.0;
   out_7252406541217060893[281] = 0.0;
   out_7252406541217060893[282] = 0.0;
   out_7252406541217060893[283] = 0.0;
   out_7252406541217060893[284] = 0.0;
   out_7252406541217060893[285] = 1.0;
   out_7252406541217060893[286] = 0.0;
   out_7252406541217060893[287] = 0.0;
   out_7252406541217060893[288] = 0.0;
   out_7252406541217060893[289] = 0.0;
   out_7252406541217060893[290] = 0.0;
   out_7252406541217060893[291] = 0.0;
   out_7252406541217060893[292] = 0.0;
   out_7252406541217060893[293] = 0.0;
   out_7252406541217060893[294] = 0.0;
   out_7252406541217060893[295] = 0.0;
   out_7252406541217060893[296] = 0.0;
   out_7252406541217060893[297] = 0.0;
   out_7252406541217060893[298] = 0.0;
   out_7252406541217060893[299] = 0.0;
   out_7252406541217060893[300] = 0.0;
   out_7252406541217060893[301] = 0.0;
   out_7252406541217060893[302] = 0.0;
   out_7252406541217060893[303] = 0.0;
   out_7252406541217060893[304] = 1.0;
   out_7252406541217060893[305] = 0.0;
   out_7252406541217060893[306] = 0.0;
   out_7252406541217060893[307] = 0.0;
   out_7252406541217060893[308] = 0.0;
   out_7252406541217060893[309] = 0.0;
   out_7252406541217060893[310] = 0.0;
   out_7252406541217060893[311] = 0.0;
   out_7252406541217060893[312] = 0.0;
   out_7252406541217060893[313] = 0.0;
   out_7252406541217060893[314] = 0.0;
   out_7252406541217060893[315] = 0.0;
   out_7252406541217060893[316] = 0.0;
   out_7252406541217060893[317] = 0.0;
   out_7252406541217060893[318] = 0.0;
   out_7252406541217060893[319] = 0.0;
   out_7252406541217060893[320] = 0.0;
   out_7252406541217060893[321] = 0.0;
   out_7252406541217060893[322] = 0.0;
   out_7252406541217060893[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_7195877540201438501) {
   out_7195877540201438501[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_7195877540201438501[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_7195877540201438501[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_7195877540201438501[3] = dt*state[12] + state[3];
   out_7195877540201438501[4] = dt*state[13] + state[4];
   out_7195877540201438501[5] = dt*state[14] + state[5];
   out_7195877540201438501[6] = state[6];
   out_7195877540201438501[7] = state[7];
   out_7195877540201438501[8] = state[8];
   out_7195877540201438501[9] = state[9];
   out_7195877540201438501[10] = state[10];
   out_7195877540201438501[11] = state[11];
   out_7195877540201438501[12] = state[12];
   out_7195877540201438501[13] = state[13];
   out_7195877540201438501[14] = state[14];
   out_7195877540201438501[15] = state[15];
   out_7195877540201438501[16] = state[16];
   out_7195877540201438501[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2191763838467757291) {
   out_2191763838467757291[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2191763838467757291[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2191763838467757291[2] = 0;
   out_2191763838467757291[3] = 0;
   out_2191763838467757291[4] = 0;
   out_2191763838467757291[5] = 0;
   out_2191763838467757291[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2191763838467757291[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2191763838467757291[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2191763838467757291[9] = 0;
   out_2191763838467757291[10] = 0;
   out_2191763838467757291[11] = 0;
   out_2191763838467757291[12] = 0;
   out_2191763838467757291[13] = 0;
   out_2191763838467757291[14] = 0;
   out_2191763838467757291[15] = 0;
   out_2191763838467757291[16] = 0;
   out_2191763838467757291[17] = 0;
   out_2191763838467757291[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2191763838467757291[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2191763838467757291[20] = 0;
   out_2191763838467757291[21] = 0;
   out_2191763838467757291[22] = 0;
   out_2191763838467757291[23] = 0;
   out_2191763838467757291[24] = 0;
   out_2191763838467757291[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2191763838467757291[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2191763838467757291[27] = 0;
   out_2191763838467757291[28] = 0;
   out_2191763838467757291[29] = 0;
   out_2191763838467757291[30] = 0;
   out_2191763838467757291[31] = 0;
   out_2191763838467757291[32] = 0;
   out_2191763838467757291[33] = 0;
   out_2191763838467757291[34] = 0;
   out_2191763838467757291[35] = 0;
   out_2191763838467757291[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2191763838467757291[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2191763838467757291[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2191763838467757291[39] = 0;
   out_2191763838467757291[40] = 0;
   out_2191763838467757291[41] = 0;
   out_2191763838467757291[42] = 0;
   out_2191763838467757291[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2191763838467757291[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2191763838467757291[45] = 0;
   out_2191763838467757291[46] = 0;
   out_2191763838467757291[47] = 0;
   out_2191763838467757291[48] = 0;
   out_2191763838467757291[49] = 0;
   out_2191763838467757291[50] = 0;
   out_2191763838467757291[51] = 0;
   out_2191763838467757291[52] = 0;
   out_2191763838467757291[53] = 0;
   out_2191763838467757291[54] = 0;
   out_2191763838467757291[55] = 0;
   out_2191763838467757291[56] = 0;
   out_2191763838467757291[57] = 1;
   out_2191763838467757291[58] = 0;
   out_2191763838467757291[59] = 0;
   out_2191763838467757291[60] = 0;
   out_2191763838467757291[61] = 0;
   out_2191763838467757291[62] = 0;
   out_2191763838467757291[63] = 0;
   out_2191763838467757291[64] = 0;
   out_2191763838467757291[65] = 0;
   out_2191763838467757291[66] = dt;
   out_2191763838467757291[67] = 0;
   out_2191763838467757291[68] = 0;
   out_2191763838467757291[69] = 0;
   out_2191763838467757291[70] = 0;
   out_2191763838467757291[71] = 0;
   out_2191763838467757291[72] = 0;
   out_2191763838467757291[73] = 0;
   out_2191763838467757291[74] = 0;
   out_2191763838467757291[75] = 0;
   out_2191763838467757291[76] = 1;
   out_2191763838467757291[77] = 0;
   out_2191763838467757291[78] = 0;
   out_2191763838467757291[79] = 0;
   out_2191763838467757291[80] = 0;
   out_2191763838467757291[81] = 0;
   out_2191763838467757291[82] = 0;
   out_2191763838467757291[83] = 0;
   out_2191763838467757291[84] = 0;
   out_2191763838467757291[85] = dt;
   out_2191763838467757291[86] = 0;
   out_2191763838467757291[87] = 0;
   out_2191763838467757291[88] = 0;
   out_2191763838467757291[89] = 0;
   out_2191763838467757291[90] = 0;
   out_2191763838467757291[91] = 0;
   out_2191763838467757291[92] = 0;
   out_2191763838467757291[93] = 0;
   out_2191763838467757291[94] = 0;
   out_2191763838467757291[95] = 1;
   out_2191763838467757291[96] = 0;
   out_2191763838467757291[97] = 0;
   out_2191763838467757291[98] = 0;
   out_2191763838467757291[99] = 0;
   out_2191763838467757291[100] = 0;
   out_2191763838467757291[101] = 0;
   out_2191763838467757291[102] = 0;
   out_2191763838467757291[103] = 0;
   out_2191763838467757291[104] = dt;
   out_2191763838467757291[105] = 0;
   out_2191763838467757291[106] = 0;
   out_2191763838467757291[107] = 0;
   out_2191763838467757291[108] = 0;
   out_2191763838467757291[109] = 0;
   out_2191763838467757291[110] = 0;
   out_2191763838467757291[111] = 0;
   out_2191763838467757291[112] = 0;
   out_2191763838467757291[113] = 0;
   out_2191763838467757291[114] = 1;
   out_2191763838467757291[115] = 0;
   out_2191763838467757291[116] = 0;
   out_2191763838467757291[117] = 0;
   out_2191763838467757291[118] = 0;
   out_2191763838467757291[119] = 0;
   out_2191763838467757291[120] = 0;
   out_2191763838467757291[121] = 0;
   out_2191763838467757291[122] = 0;
   out_2191763838467757291[123] = 0;
   out_2191763838467757291[124] = 0;
   out_2191763838467757291[125] = 0;
   out_2191763838467757291[126] = 0;
   out_2191763838467757291[127] = 0;
   out_2191763838467757291[128] = 0;
   out_2191763838467757291[129] = 0;
   out_2191763838467757291[130] = 0;
   out_2191763838467757291[131] = 0;
   out_2191763838467757291[132] = 0;
   out_2191763838467757291[133] = 1;
   out_2191763838467757291[134] = 0;
   out_2191763838467757291[135] = 0;
   out_2191763838467757291[136] = 0;
   out_2191763838467757291[137] = 0;
   out_2191763838467757291[138] = 0;
   out_2191763838467757291[139] = 0;
   out_2191763838467757291[140] = 0;
   out_2191763838467757291[141] = 0;
   out_2191763838467757291[142] = 0;
   out_2191763838467757291[143] = 0;
   out_2191763838467757291[144] = 0;
   out_2191763838467757291[145] = 0;
   out_2191763838467757291[146] = 0;
   out_2191763838467757291[147] = 0;
   out_2191763838467757291[148] = 0;
   out_2191763838467757291[149] = 0;
   out_2191763838467757291[150] = 0;
   out_2191763838467757291[151] = 0;
   out_2191763838467757291[152] = 1;
   out_2191763838467757291[153] = 0;
   out_2191763838467757291[154] = 0;
   out_2191763838467757291[155] = 0;
   out_2191763838467757291[156] = 0;
   out_2191763838467757291[157] = 0;
   out_2191763838467757291[158] = 0;
   out_2191763838467757291[159] = 0;
   out_2191763838467757291[160] = 0;
   out_2191763838467757291[161] = 0;
   out_2191763838467757291[162] = 0;
   out_2191763838467757291[163] = 0;
   out_2191763838467757291[164] = 0;
   out_2191763838467757291[165] = 0;
   out_2191763838467757291[166] = 0;
   out_2191763838467757291[167] = 0;
   out_2191763838467757291[168] = 0;
   out_2191763838467757291[169] = 0;
   out_2191763838467757291[170] = 0;
   out_2191763838467757291[171] = 1;
   out_2191763838467757291[172] = 0;
   out_2191763838467757291[173] = 0;
   out_2191763838467757291[174] = 0;
   out_2191763838467757291[175] = 0;
   out_2191763838467757291[176] = 0;
   out_2191763838467757291[177] = 0;
   out_2191763838467757291[178] = 0;
   out_2191763838467757291[179] = 0;
   out_2191763838467757291[180] = 0;
   out_2191763838467757291[181] = 0;
   out_2191763838467757291[182] = 0;
   out_2191763838467757291[183] = 0;
   out_2191763838467757291[184] = 0;
   out_2191763838467757291[185] = 0;
   out_2191763838467757291[186] = 0;
   out_2191763838467757291[187] = 0;
   out_2191763838467757291[188] = 0;
   out_2191763838467757291[189] = 0;
   out_2191763838467757291[190] = 1;
   out_2191763838467757291[191] = 0;
   out_2191763838467757291[192] = 0;
   out_2191763838467757291[193] = 0;
   out_2191763838467757291[194] = 0;
   out_2191763838467757291[195] = 0;
   out_2191763838467757291[196] = 0;
   out_2191763838467757291[197] = 0;
   out_2191763838467757291[198] = 0;
   out_2191763838467757291[199] = 0;
   out_2191763838467757291[200] = 0;
   out_2191763838467757291[201] = 0;
   out_2191763838467757291[202] = 0;
   out_2191763838467757291[203] = 0;
   out_2191763838467757291[204] = 0;
   out_2191763838467757291[205] = 0;
   out_2191763838467757291[206] = 0;
   out_2191763838467757291[207] = 0;
   out_2191763838467757291[208] = 0;
   out_2191763838467757291[209] = 1;
   out_2191763838467757291[210] = 0;
   out_2191763838467757291[211] = 0;
   out_2191763838467757291[212] = 0;
   out_2191763838467757291[213] = 0;
   out_2191763838467757291[214] = 0;
   out_2191763838467757291[215] = 0;
   out_2191763838467757291[216] = 0;
   out_2191763838467757291[217] = 0;
   out_2191763838467757291[218] = 0;
   out_2191763838467757291[219] = 0;
   out_2191763838467757291[220] = 0;
   out_2191763838467757291[221] = 0;
   out_2191763838467757291[222] = 0;
   out_2191763838467757291[223] = 0;
   out_2191763838467757291[224] = 0;
   out_2191763838467757291[225] = 0;
   out_2191763838467757291[226] = 0;
   out_2191763838467757291[227] = 0;
   out_2191763838467757291[228] = 1;
   out_2191763838467757291[229] = 0;
   out_2191763838467757291[230] = 0;
   out_2191763838467757291[231] = 0;
   out_2191763838467757291[232] = 0;
   out_2191763838467757291[233] = 0;
   out_2191763838467757291[234] = 0;
   out_2191763838467757291[235] = 0;
   out_2191763838467757291[236] = 0;
   out_2191763838467757291[237] = 0;
   out_2191763838467757291[238] = 0;
   out_2191763838467757291[239] = 0;
   out_2191763838467757291[240] = 0;
   out_2191763838467757291[241] = 0;
   out_2191763838467757291[242] = 0;
   out_2191763838467757291[243] = 0;
   out_2191763838467757291[244] = 0;
   out_2191763838467757291[245] = 0;
   out_2191763838467757291[246] = 0;
   out_2191763838467757291[247] = 1;
   out_2191763838467757291[248] = 0;
   out_2191763838467757291[249] = 0;
   out_2191763838467757291[250] = 0;
   out_2191763838467757291[251] = 0;
   out_2191763838467757291[252] = 0;
   out_2191763838467757291[253] = 0;
   out_2191763838467757291[254] = 0;
   out_2191763838467757291[255] = 0;
   out_2191763838467757291[256] = 0;
   out_2191763838467757291[257] = 0;
   out_2191763838467757291[258] = 0;
   out_2191763838467757291[259] = 0;
   out_2191763838467757291[260] = 0;
   out_2191763838467757291[261] = 0;
   out_2191763838467757291[262] = 0;
   out_2191763838467757291[263] = 0;
   out_2191763838467757291[264] = 0;
   out_2191763838467757291[265] = 0;
   out_2191763838467757291[266] = 1;
   out_2191763838467757291[267] = 0;
   out_2191763838467757291[268] = 0;
   out_2191763838467757291[269] = 0;
   out_2191763838467757291[270] = 0;
   out_2191763838467757291[271] = 0;
   out_2191763838467757291[272] = 0;
   out_2191763838467757291[273] = 0;
   out_2191763838467757291[274] = 0;
   out_2191763838467757291[275] = 0;
   out_2191763838467757291[276] = 0;
   out_2191763838467757291[277] = 0;
   out_2191763838467757291[278] = 0;
   out_2191763838467757291[279] = 0;
   out_2191763838467757291[280] = 0;
   out_2191763838467757291[281] = 0;
   out_2191763838467757291[282] = 0;
   out_2191763838467757291[283] = 0;
   out_2191763838467757291[284] = 0;
   out_2191763838467757291[285] = 1;
   out_2191763838467757291[286] = 0;
   out_2191763838467757291[287] = 0;
   out_2191763838467757291[288] = 0;
   out_2191763838467757291[289] = 0;
   out_2191763838467757291[290] = 0;
   out_2191763838467757291[291] = 0;
   out_2191763838467757291[292] = 0;
   out_2191763838467757291[293] = 0;
   out_2191763838467757291[294] = 0;
   out_2191763838467757291[295] = 0;
   out_2191763838467757291[296] = 0;
   out_2191763838467757291[297] = 0;
   out_2191763838467757291[298] = 0;
   out_2191763838467757291[299] = 0;
   out_2191763838467757291[300] = 0;
   out_2191763838467757291[301] = 0;
   out_2191763838467757291[302] = 0;
   out_2191763838467757291[303] = 0;
   out_2191763838467757291[304] = 1;
   out_2191763838467757291[305] = 0;
   out_2191763838467757291[306] = 0;
   out_2191763838467757291[307] = 0;
   out_2191763838467757291[308] = 0;
   out_2191763838467757291[309] = 0;
   out_2191763838467757291[310] = 0;
   out_2191763838467757291[311] = 0;
   out_2191763838467757291[312] = 0;
   out_2191763838467757291[313] = 0;
   out_2191763838467757291[314] = 0;
   out_2191763838467757291[315] = 0;
   out_2191763838467757291[316] = 0;
   out_2191763838467757291[317] = 0;
   out_2191763838467757291[318] = 0;
   out_2191763838467757291[319] = 0;
   out_2191763838467757291[320] = 0;
   out_2191763838467757291[321] = 0;
   out_2191763838467757291[322] = 0;
   out_2191763838467757291[323] = 1;
}
void h_4(double *state, double *unused, double *out_6710764914604440332) {
   out_6710764914604440332[0] = state[6] + state[9];
   out_6710764914604440332[1] = state[7] + state[10];
   out_6710764914604440332[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_9072105267123357754) {
   out_9072105267123357754[0] = 0;
   out_9072105267123357754[1] = 0;
   out_9072105267123357754[2] = 0;
   out_9072105267123357754[3] = 0;
   out_9072105267123357754[4] = 0;
   out_9072105267123357754[5] = 0;
   out_9072105267123357754[6] = 1;
   out_9072105267123357754[7] = 0;
   out_9072105267123357754[8] = 0;
   out_9072105267123357754[9] = 1;
   out_9072105267123357754[10] = 0;
   out_9072105267123357754[11] = 0;
   out_9072105267123357754[12] = 0;
   out_9072105267123357754[13] = 0;
   out_9072105267123357754[14] = 0;
   out_9072105267123357754[15] = 0;
   out_9072105267123357754[16] = 0;
   out_9072105267123357754[17] = 0;
   out_9072105267123357754[18] = 0;
   out_9072105267123357754[19] = 0;
   out_9072105267123357754[20] = 0;
   out_9072105267123357754[21] = 0;
   out_9072105267123357754[22] = 0;
   out_9072105267123357754[23] = 0;
   out_9072105267123357754[24] = 0;
   out_9072105267123357754[25] = 1;
   out_9072105267123357754[26] = 0;
   out_9072105267123357754[27] = 0;
   out_9072105267123357754[28] = 1;
   out_9072105267123357754[29] = 0;
   out_9072105267123357754[30] = 0;
   out_9072105267123357754[31] = 0;
   out_9072105267123357754[32] = 0;
   out_9072105267123357754[33] = 0;
   out_9072105267123357754[34] = 0;
   out_9072105267123357754[35] = 0;
   out_9072105267123357754[36] = 0;
   out_9072105267123357754[37] = 0;
   out_9072105267123357754[38] = 0;
   out_9072105267123357754[39] = 0;
   out_9072105267123357754[40] = 0;
   out_9072105267123357754[41] = 0;
   out_9072105267123357754[42] = 0;
   out_9072105267123357754[43] = 0;
   out_9072105267123357754[44] = 1;
   out_9072105267123357754[45] = 0;
   out_9072105267123357754[46] = 0;
   out_9072105267123357754[47] = 1;
   out_9072105267123357754[48] = 0;
   out_9072105267123357754[49] = 0;
   out_9072105267123357754[50] = 0;
   out_9072105267123357754[51] = 0;
   out_9072105267123357754[52] = 0;
   out_9072105267123357754[53] = 0;
}
void h_10(double *state, double *unused, double *out_5397643117837077736) {
   out_5397643117837077736[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5397643117837077736[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5397643117837077736[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8486068256269040489) {
   out_8486068256269040489[0] = 0;
   out_8486068256269040489[1] = 9.8100000000000005*cos(state[1]);
   out_8486068256269040489[2] = 0;
   out_8486068256269040489[3] = 0;
   out_8486068256269040489[4] = -state[8];
   out_8486068256269040489[5] = state[7];
   out_8486068256269040489[6] = 0;
   out_8486068256269040489[7] = state[5];
   out_8486068256269040489[8] = -state[4];
   out_8486068256269040489[9] = 0;
   out_8486068256269040489[10] = 0;
   out_8486068256269040489[11] = 0;
   out_8486068256269040489[12] = 1;
   out_8486068256269040489[13] = 0;
   out_8486068256269040489[14] = 0;
   out_8486068256269040489[15] = 1;
   out_8486068256269040489[16] = 0;
   out_8486068256269040489[17] = 0;
   out_8486068256269040489[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8486068256269040489[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8486068256269040489[20] = 0;
   out_8486068256269040489[21] = state[8];
   out_8486068256269040489[22] = 0;
   out_8486068256269040489[23] = -state[6];
   out_8486068256269040489[24] = -state[5];
   out_8486068256269040489[25] = 0;
   out_8486068256269040489[26] = state[3];
   out_8486068256269040489[27] = 0;
   out_8486068256269040489[28] = 0;
   out_8486068256269040489[29] = 0;
   out_8486068256269040489[30] = 0;
   out_8486068256269040489[31] = 1;
   out_8486068256269040489[32] = 0;
   out_8486068256269040489[33] = 0;
   out_8486068256269040489[34] = 1;
   out_8486068256269040489[35] = 0;
   out_8486068256269040489[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8486068256269040489[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8486068256269040489[38] = 0;
   out_8486068256269040489[39] = -state[7];
   out_8486068256269040489[40] = state[6];
   out_8486068256269040489[41] = 0;
   out_8486068256269040489[42] = state[4];
   out_8486068256269040489[43] = -state[3];
   out_8486068256269040489[44] = 0;
   out_8486068256269040489[45] = 0;
   out_8486068256269040489[46] = 0;
   out_8486068256269040489[47] = 0;
   out_8486068256269040489[48] = 0;
   out_8486068256269040489[49] = 0;
   out_8486068256269040489[50] = 1;
   out_8486068256269040489[51] = 0;
   out_8486068256269040489[52] = 0;
   out_8486068256269040489[53] = 1;
}
void h_13(double *state, double *unused, double *out_1020156160635096483) {
   out_1020156160635096483[0] = state[3];
   out_1020156160635096483[1] = state[4];
   out_1020156160635096483[2] = state[5];
}
void H_13(double *state, double *unused, double *out_5859831441791024953) {
   out_5859831441791024953[0] = 0;
   out_5859831441791024953[1] = 0;
   out_5859831441791024953[2] = 0;
   out_5859831441791024953[3] = 1;
   out_5859831441791024953[4] = 0;
   out_5859831441791024953[5] = 0;
   out_5859831441791024953[6] = 0;
   out_5859831441791024953[7] = 0;
   out_5859831441791024953[8] = 0;
   out_5859831441791024953[9] = 0;
   out_5859831441791024953[10] = 0;
   out_5859831441791024953[11] = 0;
   out_5859831441791024953[12] = 0;
   out_5859831441791024953[13] = 0;
   out_5859831441791024953[14] = 0;
   out_5859831441791024953[15] = 0;
   out_5859831441791024953[16] = 0;
   out_5859831441791024953[17] = 0;
   out_5859831441791024953[18] = 0;
   out_5859831441791024953[19] = 0;
   out_5859831441791024953[20] = 0;
   out_5859831441791024953[21] = 0;
   out_5859831441791024953[22] = 1;
   out_5859831441791024953[23] = 0;
   out_5859831441791024953[24] = 0;
   out_5859831441791024953[25] = 0;
   out_5859831441791024953[26] = 0;
   out_5859831441791024953[27] = 0;
   out_5859831441791024953[28] = 0;
   out_5859831441791024953[29] = 0;
   out_5859831441791024953[30] = 0;
   out_5859831441791024953[31] = 0;
   out_5859831441791024953[32] = 0;
   out_5859831441791024953[33] = 0;
   out_5859831441791024953[34] = 0;
   out_5859831441791024953[35] = 0;
   out_5859831441791024953[36] = 0;
   out_5859831441791024953[37] = 0;
   out_5859831441791024953[38] = 0;
   out_5859831441791024953[39] = 0;
   out_5859831441791024953[40] = 0;
   out_5859831441791024953[41] = 1;
   out_5859831441791024953[42] = 0;
   out_5859831441791024953[43] = 0;
   out_5859831441791024953[44] = 0;
   out_5859831441791024953[45] = 0;
   out_5859831441791024953[46] = 0;
   out_5859831441791024953[47] = 0;
   out_5859831441791024953[48] = 0;
   out_5859831441791024953[49] = 0;
   out_5859831441791024953[50] = 0;
   out_5859831441791024953[51] = 0;
   out_5859831441791024953[52] = 0;
   out_5859831441791024953[53] = 0;
}
void h_14(double *state, double *unused, double *out_6027370464870412024) {
   out_6027370464870412024[0] = state[6];
   out_6027370464870412024[1] = state[7];
   out_6027370464870412024[2] = state[8];
}
void H_14(double *state, double *unused, double *out_5108864410783873225) {
   out_5108864410783873225[0] = 0;
   out_5108864410783873225[1] = 0;
   out_5108864410783873225[2] = 0;
   out_5108864410783873225[3] = 0;
   out_5108864410783873225[4] = 0;
   out_5108864410783873225[5] = 0;
   out_5108864410783873225[6] = 1;
   out_5108864410783873225[7] = 0;
   out_5108864410783873225[8] = 0;
   out_5108864410783873225[9] = 0;
   out_5108864410783873225[10] = 0;
   out_5108864410783873225[11] = 0;
   out_5108864410783873225[12] = 0;
   out_5108864410783873225[13] = 0;
   out_5108864410783873225[14] = 0;
   out_5108864410783873225[15] = 0;
   out_5108864410783873225[16] = 0;
   out_5108864410783873225[17] = 0;
   out_5108864410783873225[18] = 0;
   out_5108864410783873225[19] = 0;
   out_5108864410783873225[20] = 0;
   out_5108864410783873225[21] = 0;
   out_5108864410783873225[22] = 0;
   out_5108864410783873225[23] = 0;
   out_5108864410783873225[24] = 0;
   out_5108864410783873225[25] = 1;
   out_5108864410783873225[26] = 0;
   out_5108864410783873225[27] = 0;
   out_5108864410783873225[28] = 0;
   out_5108864410783873225[29] = 0;
   out_5108864410783873225[30] = 0;
   out_5108864410783873225[31] = 0;
   out_5108864410783873225[32] = 0;
   out_5108864410783873225[33] = 0;
   out_5108864410783873225[34] = 0;
   out_5108864410783873225[35] = 0;
   out_5108864410783873225[36] = 0;
   out_5108864410783873225[37] = 0;
   out_5108864410783873225[38] = 0;
   out_5108864410783873225[39] = 0;
   out_5108864410783873225[40] = 0;
   out_5108864410783873225[41] = 0;
   out_5108864410783873225[42] = 0;
   out_5108864410783873225[43] = 0;
   out_5108864410783873225[44] = 1;
   out_5108864410783873225[45] = 0;
   out_5108864410783873225[46] = 0;
   out_5108864410783873225[47] = 0;
   out_5108864410783873225[48] = 0;
   out_5108864410783873225[49] = 0;
   out_5108864410783873225[50] = 0;
   out_5108864410783873225[51] = 0;
   out_5108864410783873225[52] = 0;
   out_5108864410783873225[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5436717349763929250) {
  err_fun(nom_x, delta_x, out_5436717349763929250);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2267989734965085487) {
  inv_err_fun(nom_x, true_x, out_2267989734965085487);
}
void pose_H_mod_fun(double *state, double *out_7252406541217060893) {
  H_mod_fun(state, out_7252406541217060893);
}
void pose_f_fun(double *state, double dt, double *out_7195877540201438501) {
  f_fun(state,  dt, out_7195877540201438501);
}
void pose_F_fun(double *state, double dt, double *out_2191763838467757291) {
  F_fun(state,  dt, out_2191763838467757291);
}
void pose_h_4(double *state, double *unused, double *out_6710764914604440332) {
  h_4(state, unused, out_6710764914604440332);
}
void pose_H_4(double *state, double *unused, double *out_9072105267123357754) {
  H_4(state, unused, out_9072105267123357754);
}
void pose_h_10(double *state, double *unused, double *out_5397643117837077736) {
  h_10(state, unused, out_5397643117837077736);
}
void pose_H_10(double *state, double *unused, double *out_8486068256269040489) {
  H_10(state, unused, out_8486068256269040489);
}
void pose_h_13(double *state, double *unused, double *out_1020156160635096483) {
  h_13(state, unused, out_1020156160635096483);
}
void pose_H_13(double *state, double *unused, double *out_5859831441791024953) {
  H_13(state, unused, out_5859831441791024953);
}
void pose_h_14(double *state, double *unused, double *out_6027370464870412024) {
  h_14(state, unused, out_6027370464870412024);
}
void pose_H_14(double *state, double *unused, double *out_5108864410783873225) {
  H_14(state, unused, out_5108864410783873225);
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
