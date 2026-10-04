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
void err_fun(double *nom_x, double *delta_x, double *out_3009922513179117509) {
   out_3009922513179117509[0] = delta_x[0] + nom_x[0];
   out_3009922513179117509[1] = delta_x[1] + nom_x[1];
   out_3009922513179117509[2] = delta_x[2] + nom_x[2];
   out_3009922513179117509[3] = delta_x[3] + nom_x[3];
   out_3009922513179117509[4] = delta_x[4] + nom_x[4];
   out_3009922513179117509[5] = delta_x[5] + nom_x[5];
   out_3009922513179117509[6] = delta_x[6] + nom_x[6];
   out_3009922513179117509[7] = delta_x[7] + nom_x[7];
   out_3009922513179117509[8] = delta_x[8] + nom_x[8];
   out_3009922513179117509[9] = delta_x[9] + nom_x[9];
   out_3009922513179117509[10] = delta_x[10] + nom_x[10];
   out_3009922513179117509[11] = delta_x[11] + nom_x[11];
   out_3009922513179117509[12] = delta_x[12] + nom_x[12];
   out_3009922513179117509[13] = delta_x[13] + nom_x[13];
   out_3009922513179117509[14] = delta_x[14] + nom_x[14];
   out_3009922513179117509[15] = delta_x[15] + nom_x[15];
   out_3009922513179117509[16] = delta_x[16] + nom_x[16];
   out_3009922513179117509[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_975857412122476284) {
   out_975857412122476284[0] = -nom_x[0] + true_x[0];
   out_975857412122476284[1] = -nom_x[1] + true_x[1];
   out_975857412122476284[2] = -nom_x[2] + true_x[2];
   out_975857412122476284[3] = -nom_x[3] + true_x[3];
   out_975857412122476284[4] = -nom_x[4] + true_x[4];
   out_975857412122476284[5] = -nom_x[5] + true_x[5];
   out_975857412122476284[6] = -nom_x[6] + true_x[6];
   out_975857412122476284[7] = -nom_x[7] + true_x[7];
   out_975857412122476284[8] = -nom_x[8] + true_x[8];
   out_975857412122476284[9] = -nom_x[9] + true_x[9];
   out_975857412122476284[10] = -nom_x[10] + true_x[10];
   out_975857412122476284[11] = -nom_x[11] + true_x[11];
   out_975857412122476284[12] = -nom_x[12] + true_x[12];
   out_975857412122476284[13] = -nom_x[13] + true_x[13];
   out_975857412122476284[14] = -nom_x[14] + true_x[14];
   out_975857412122476284[15] = -nom_x[15] + true_x[15];
   out_975857412122476284[16] = -nom_x[16] + true_x[16];
   out_975857412122476284[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5701585413794445279) {
   out_5701585413794445279[0] = 1.0;
   out_5701585413794445279[1] = 0.0;
   out_5701585413794445279[2] = 0.0;
   out_5701585413794445279[3] = 0.0;
   out_5701585413794445279[4] = 0.0;
   out_5701585413794445279[5] = 0.0;
   out_5701585413794445279[6] = 0.0;
   out_5701585413794445279[7] = 0.0;
   out_5701585413794445279[8] = 0.0;
   out_5701585413794445279[9] = 0.0;
   out_5701585413794445279[10] = 0.0;
   out_5701585413794445279[11] = 0.0;
   out_5701585413794445279[12] = 0.0;
   out_5701585413794445279[13] = 0.0;
   out_5701585413794445279[14] = 0.0;
   out_5701585413794445279[15] = 0.0;
   out_5701585413794445279[16] = 0.0;
   out_5701585413794445279[17] = 0.0;
   out_5701585413794445279[18] = 0.0;
   out_5701585413794445279[19] = 1.0;
   out_5701585413794445279[20] = 0.0;
   out_5701585413794445279[21] = 0.0;
   out_5701585413794445279[22] = 0.0;
   out_5701585413794445279[23] = 0.0;
   out_5701585413794445279[24] = 0.0;
   out_5701585413794445279[25] = 0.0;
   out_5701585413794445279[26] = 0.0;
   out_5701585413794445279[27] = 0.0;
   out_5701585413794445279[28] = 0.0;
   out_5701585413794445279[29] = 0.0;
   out_5701585413794445279[30] = 0.0;
   out_5701585413794445279[31] = 0.0;
   out_5701585413794445279[32] = 0.0;
   out_5701585413794445279[33] = 0.0;
   out_5701585413794445279[34] = 0.0;
   out_5701585413794445279[35] = 0.0;
   out_5701585413794445279[36] = 0.0;
   out_5701585413794445279[37] = 0.0;
   out_5701585413794445279[38] = 1.0;
   out_5701585413794445279[39] = 0.0;
   out_5701585413794445279[40] = 0.0;
   out_5701585413794445279[41] = 0.0;
   out_5701585413794445279[42] = 0.0;
   out_5701585413794445279[43] = 0.0;
   out_5701585413794445279[44] = 0.0;
   out_5701585413794445279[45] = 0.0;
   out_5701585413794445279[46] = 0.0;
   out_5701585413794445279[47] = 0.0;
   out_5701585413794445279[48] = 0.0;
   out_5701585413794445279[49] = 0.0;
   out_5701585413794445279[50] = 0.0;
   out_5701585413794445279[51] = 0.0;
   out_5701585413794445279[52] = 0.0;
   out_5701585413794445279[53] = 0.0;
   out_5701585413794445279[54] = 0.0;
   out_5701585413794445279[55] = 0.0;
   out_5701585413794445279[56] = 0.0;
   out_5701585413794445279[57] = 1.0;
   out_5701585413794445279[58] = 0.0;
   out_5701585413794445279[59] = 0.0;
   out_5701585413794445279[60] = 0.0;
   out_5701585413794445279[61] = 0.0;
   out_5701585413794445279[62] = 0.0;
   out_5701585413794445279[63] = 0.0;
   out_5701585413794445279[64] = 0.0;
   out_5701585413794445279[65] = 0.0;
   out_5701585413794445279[66] = 0.0;
   out_5701585413794445279[67] = 0.0;
   out_5701585413794445279[68] = 0.0;
   out_5701585413794445279[69] = 0.0;
   out_5701585413794445279[70] = 0.0;
   out_5701585413794445279[71] = 0.0;
   out_5701585413794445279[72] = 0.0;
   out_5701585413794445279[73] = 0.0;
   out_5701585413794445279[74] = 0.0;
   out_5701585413794445279[75] = 0.0;
   out_5701585413794445279[76] = 1.0;
   out_5701585413794445279[77] = 0.0;
   out_5701585413794445279[78] = 0.0;
   out_5701585413794445279[79] = 0.0;
   out_5701585413794445279[80] = 0.0;
   out_5701585413794445279[81] = 0.0;
   out_5701585413794445279[82] = 0.0;
   out_5701585413794445279[83] = 0.0;
   out_5701585413794445279[84] = 0.0;
   out_5701585413794445279[85] = 0.0;
   out_5701585413794445279[86] = 0.0;
   out_5701585413794445279[87] = 0.0;
   out_5701585413794445279[88] = 0.0;
   out_5701585413794445279[89] = 0.0;
   out_5701585413794445279[90] = 0.0;
   out_5701585413794445279[91] = 0.0;
   out_5701585413794445279[92] = 0.0;
   out_5701585413794445279[93] = 0.0;
   out_5701585413794445279[94] = 0.0;
   out_5701585413794445279[95] = 1.0;
   out_5701585413794445279[96] = 0.0;
   out_5701585413794445279[97] = 0.0;
   out_5701585413794445279[98] = 0.0;
   out_5701585413794445279[99] = 0.0;
   out_5701585413794445279[100] = 0.0;
   out_5701585413794445279[101] = 0.0;
   out_5701585413794445279[102] = 0.0;
   out_5701585413794445279[103] = 0.0;
   out_5701585413794445279[104] = 0.0;
   out_5701585413794445279[105] = 0.0;
   out_5701585413794445279[106] = 0.0;
   out_5701585413794445279[107] = 0.0;
   out_5701585413794445279[108] = 0.0;
   out_5701585413794445279[109] = 0.0;
   out_5701585413794445279[110] = 0.0;
   out_5701585413794445279[111] = 0.0;
   out_5701585413794445279[112] = 0.0;
   out_5701585413794445279[113] = 0.0;
   out_5701585413794445279[114] = 1.0;
   out_5701585413794445279[115] = 0.0;
   out_5701585413794445279[116] = 0.0;
   out_5701585413794445279[117] = 0.0;
   out_5701585413794445279[118] = 0.0;
   out_5701585413794445279[119] = 0.0;
   out_5701585413794445279[120] = 0.0;
   out_5701585413794445279[121] = 0.0;
   out_5701585413794445279[122] = 0.0;
   out_5701585413794445279[123] = 0.0;
   out_5701585413794445279[124] = 0.0;
   out_5701585413794445279[125] = 0.0;
   out_5701585413794445279[126] = 0.0;
   out_5701585413794445279[127] = 0.0;
   out_5701585413794445279[128] = 0.0;
   out_5701585413794445279[129] = 0.0;
   out_5701585413794445279[130] = 0.0;
   out_5701585413794445279[131] = 0.0;
   out_5701585413794445279[132] = 0.0;
   out_5701585413794445279[133] = 1.0;
   out_5701585413794445279[134] = 0.0;
   out_5701585413794445279[135] = 0.0;
   out_5701585413794445279[136] = 0.0;
   out_5701585413794445279[137] = 0.0;
   out_5701585413794445279[138] = 0.0;
   out_5701585413794445279[139] = 0.0;
   out_5701585413794445279[140] = 0.0;
   out_5701585413794445279[141] = 0.0;
   out_5701585413794445279[142] = 0.0;
   out_5701585413794445279[143] = 0.0;
   out_5701585413794445279[144] = 0.0;
   out_5701585413794445279[145] = 0.0;
   out_5701585413794445279[146] = 0.0;
   out_5701585413794445279[147] = 0.0;
   out_5701585413794445279[148] = 0.0;
   out_5701585413794445279[149] = 0.0;
   out_5701585413794445279[150] = 0.0;
   out_5701585413794445279[151] = 0.0;
   out_5701585413794445279[152] = 1.0;
   out_5701585413794445279[153] = 0.0;
   out_5701585413794445279[154] = 0.0;
   out_5701585413794445279[155] = 0.0;
   out_5701585413794445279[156] = 0.0;
   out_5701585413794445279[157] = 0.0;
   out_5701585413794445279[158] = 0.0;
   out_5701585413794445279[159] = 0.0;
   out_5701585413794445279[160] = 0.0;
   out_5701585413794445279[161] = 0.0;
   out_5701585413794445279[162] = 0.0;
   out_5701585413794445279[163] = 0.0;
   out_5701585413794445279[164] = 0.0;
   out_5701585413794445279[165] = 0.0;
   out_5701585413794445279[166] = 0.0;
   out_5701585413794445279[167] = 0.0;
   out_5701585413794445279[168] = 0.0;
   out_5701585413794445279[169] = 0.0;
   out_5701585413794445279[170] = 0.0;
   out_5701585413794445279[171] = 1.0;
   out_5701585413794445279[172] = 0.0;
   out_5701585413794445279[173] = 0.0;
   out_5701585413794445279[174] = 0.0;
   out_5701585413794445279[175] = 0.0;
   out_5701585413794445279[176] = 0.0;
   out_5701585413794445279[177] = 0.0;
   out_5701585413794445279[178] = 0.0;
   out_5701585413794445279[179] = 0.0;
   out_5701585413794445279[180] = 0.0;
   out_5701585413794445279[181] = 0.0;
   out_5701585413794445279[182] = 0.0;
   out_5701585413794445279[183] = 0.0;
   out_5701585413794445279[184] = 0.0;
   out_5701585413794445279[185] = 0.0;
   out_5701585413794445279[186] = 0.0;
   out_5701585413794445279[187] = 0.0;
   out_5701585413794445279[188] = 0.0;
   out_5701585413794445279[189] = 0.0;
   out_5701585413794445279[190] = 1.0;
   out_5701585413794445279[191] = 0.0;
   out_5701585413794445279[192] = 0.0;
   out_5701585413794445279[193] = 0.0;
   out_5701585413794445279[194] = 0.0;
   out_5701585413794445279[195] = 0.0;
   out_5701585413794445279[196] = 0.0;
   out_5701585413794445279[197] = 0.0;
   out_5701585413794445279[198] = 0.0;
   out_5701585413794445279[199] = 0.0;
   out_5701585413794445279[200] = 0.0;
   out_5701585413794445279[201] = 0.0;
   out_5701585413794445279[202] = 0.0;
   out_5701585413794445279[203] = 0.0;
   out_5701585413794445279[204] = 0.0;
   out_5701585413794445279[205] = 0.0;
   out_5701585413794445279[206] = 0.0;
   out_5701585413794445279[207] = 0.0;
   out_5701585413794445279[208] = 0.0;
   out_5701585413794445279[209] = 1.0;
   out_5701585413794445279[210] = 0.0;
   out_5701585413794445279[211] = 0.0;
   out_5701585413794445279[212] = 0.0;
   out_5701585413794445279[213] = 0.0;
   out_5701585413794445279[214] = 0.0;
   out_5701585413794445279[215] = 0.0;
   out_5701585413794445279[216] = 0.0;
   out_5701585413794445279[217] = 0.0;
   out_5701585413794445279[218] = 0.0;
   out_5701585413794445279[219] = 0.0;
   out_5701585413794445279[220] = 0.0;
   out_5701585413794445279[221] = 0.0;
   out_5701585413794445279[222] = 0.0;
   out_5701585413794445279[223] = 0.0;
   out_5701585413794445279[224] = 0.0;
   out_5701585413794445279[225] = 0.0;
   out_5701585413794445279[226] = 0.0;
   out_5701585413794445279[227] = 0.0;
   out_5701585413794445279[228] = 1.0;
   out_5701585413794445279[229] = 0.0;
   out_5701585413794445279[230] = 0.0;
   out_5701585413794445279[231] = 0.0;
   out_5701585413794445279[232] = 0.0;
   out_5701585413794445279[233] = 0.0;
   out_5701585413794445279[234] = 0.0;
   out_5701585413794445279[235] = 0.0;
   out_5701585413794445279[236] = 0.0;
   out_5701585413794445279[237] = 0.0;
   out_5701585413794445279[238] = 0.0;
   out_5701585413794445279[239] = 0.0;
   out_5701585413794445279[240] = 0.0;
   out_5701585413794445279[241] = 0.0;
   out_5701585413794445279[242] = 0.0;
   out_5701585413794445279[243] = 0.0;
   out_5701585413794445279[244] = 0.0;
   out_5701585413794445279[245] = 0.0;
   out_5701585413794445279[246] = 0.0;
   out_5701585413794445279[247] = 1.0;
   out_5701585413794445279[248] = 0.0;
   out_5701585413794445279[249] = 0.0;
   out_5701585413794445279[250] = 0.0;
   out_5701585413794445279[251] = 0.0;
   out_5701585413794445279[252] = 0.0;
   out_5701585413794445279[253] = 0.0;
   out_5701585413794445279[254] = 0.0;
   out_5701585413794445279[255] = 0.0;
   out_5701585413794445279[256] = 0.0;
   out_5701585413794445279[257] = 0.0;
   out_5701585413794445279[258] = 0.0;
   out_5701585413794445279[259] = 0.0;
   out_5701585413794445279[260] = 0.0;
   out_5701585413794445279[261] = 0.0;
   out_5701585413794445279[262] = 0.0;
   out_5701585413794445279[263] = 0.0;
   out_5701585413794445279[264] = 0.0;
   out_5701585413794445279[265] = 0.0;
   out_5701585413794445279[266] = 1.0;
   out_5701585413794445279[267] = 0.0;
   out_5701585413794445279[268] = 0.0;
   out_5701585413794445279[269] = 0.0;
   out_5701585413794445279[270] = 0.0;
   out_5701585413794445279[271] = 0.0;
   out_5701585413794445279[272] = 0.0;
   out_5701585413794445279[273] = 0.0;
   out_5701585413794445279[274] = 0.0;
   out_5701585413794445279[275] = 0.0;
   out_5701585413794445279[276] = 0.0;
   out_5701585413794445279[277] = 0.0;
   out_5701585413794445279[278] = 0.0;
   out_5701585413794445279[279] = 0.0;
   out_5701585413794445279[280] = 0.0;
   out_5701585413794445279[281] = 0.0;
   out_5701585413794445279[282] = 0.0;
   out_5701585413794445279[283] = 0.0;
   out_5701585413794445279[284] = 0.0;
   out_5701585413794445279[285] = 1.0;
   out_5701585413794445279[286] = 0.0;
   out_5701585413794445279[287] = 0.0;
   out_5701585413794445279[288] = 0.0;
   out_5701585413794445279[289] = 0.0;
   out_5701585413794445279[290] = 0.0;
   out_5701585413794445279[291] = 0.0;
   out_5701585413794445279[292] = 0.0;
   out_5701585413794445279[293] = 0.0;
   out_5701585413794445279[294] = 0.0;
   out_5701585413794445279[295] = 0.0;
   out_5701585413794445279[296] = 0.0;
   out_5701585413794445279[297] = 0.0;
   out_5701585413794445279[298] = 0.0;
   out_5701585413794445279[299] = 0.0;
   out_5701585413794445279[300] = 0.0;
   out_5701585413794445279[301] = 0.0;
   out_5701585413794445279[302] = 0.0;
   out_5701585413794445279[303] = 0.0;
   out_5701585413794445279[304] = 1.0;
   out_5701585413794445279[305] = 0.0;
   out_5701585413794445279[306] = 0.0;
   out_5701585413794445279[307] = 0.0;
   out_5701585413794445279[308] = 0.0;
   out_5701585413794445279[309] = 0.0;
   out_5701585413794445279[310] = 0.0;
   out_5701585413794445279[311] = 0.0;
   out_5701585413794445279[312] = 0.0;
   out_5701585413794445279[313] = 0.0;
   out_5701585413794445279[314] = 0.0;
   out_5701585413794445279[315] = 0.0;
   out_5701585413794445279[316] = 0.0;
   out_5701585413794445279[317] = 0.0;
   out_5701585413794445279[318] = 0.0;
   out_5701585413794445279[319] = 0.0;
   out_5701585413794445279[320] = 0.0;
   out_5701585413794445279[321] = 0.0;
   out_5701585413794445279[322] = 0.0;
   out_5701585413794445279[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_7100436431164388549) {
   out_7100436431164388549[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_7100436431164388549[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_7100436431164388549[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_7100436431164388549[3] = dt*state[12] + state[3];
   out_7100436431164388549[4] = dt*state[13] + state[4];
   out_7100436431164388549[5] = dt*state[14] + state[5];
   out_7100436431164388549[6] = state[6];
   out_7100436431164388549[7] = state[7];
   out_7100436431164388549[8] = state[8];
   out_7100436431164388549[9] = state[9];
   out_7100436431164388549[10] = state[10];
   out_7100436431164388549[11] = state[11];
   out_7100436431164388549[12] = state[12];
   out_7100436431164388549[13] = state[13];
   out_7100436431164388549[14] = state[14];
   out_7100436431164388549[15] = state[15];
   out_7100436431164388549[16] = state[16];
   out_7100436431164388549[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4695823766962492888) {
   out_4695823766962492888[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695823766962492888[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695823766962492888[2] = 0;
   out_4695823766962492888[3] = 0;
   out_4695823766962492888[4] = 0;
   out_4695823766962492888[5] = 0;
   out_4695823766962492888[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695823766962492888[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695823766962492888[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695823766962492888[9] = 0;
   out_4695823766962492888[10] = 0;
   out_4695823766962492888[11] = 0;
   out_4695823766962492888[12] = 0;
   out_4695823766962492888[13] = 0;
   out_4695823766962492888[14] = 0;
   out_4695823766962492888[15] = 0;
   out_4695823766962492888[16] = 0;
   out_4695823766962492888[17] = 0;
   out_4695823766962492888[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695823766962492888[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695823766962492888[20] = 0;
   out_4695823766962492888[21] = 0;
   out_4695823766962492888[22] = 0;
   out_4695823766962492888[23] = 0;
   out_4695823766962492888[24] = 0;
   out_4695823766962492888[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695823766962492888[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695823766962492888[27] = 0;
   out_4695823766962492888[28] = 0;
   out_4695823766962492888[29] = 0;
   out_4695823766962492888[30] = 0;
   out_4695823766962492888[31] = 0;
   out_4695823766962492888[32] = 0;
   out_4695823766962492888[33] = 0;
   out_4695823766962492888[34] = 0;
   out_4695823766962492888[35] = 0;
   out_4695823766962492888[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695823766962492888[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695823766962492888[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695823766962492888[39] = 0;
   out_4695823766962492888[40] = 0;
   out_4695823766962492888[41] = 0;
   out_4695823766962492888[42] = 0;
   out_4695823766962492888[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695823766962492888[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695823766962492888[45] = 0;
   out_4695823766962492888[46] = 0;
   out_4695823766962492888[47] = 0;
   out_4695823766962492888[48] = 0;
   out_4695823766962492888[49] = 0;
   out_4695823766962492888[50] = 0;
   out_4695823766962492888[51] = 0;
   out_4695823766962492888[52] = 0;
   out_4695823766962492888[53] = 0;
   out_4695823766962492888[54] = 0;
   out_4695823766962492888[55] = 0;
   out_4695823766962492888[56] = 0;
   out_4695823766962492888[57] = 1;
   out_4695823766962492888[58] = 0;
   out_4695823766962492888[59] = 0;
   out_4695823766962492888[60] = 0;
   out_4695823766962492888[61] = 0;
   out_4695823766962492888[62] = 0;
   out_4695823766962492888[63] = 0;
   out_4695823766962492888[64] = 0;
   out_4695823766962492888[65] = 0;
   out_4695823766962492888[66] = dt;
   out_4695823766962492888[67] = 0;
   out_4695823766962492888[68] = 0;
   out_4695823766962492888[69] = 0;
   out_4695823766962492888[70] = 0;
   out_4695823766962492888[71] = 0;
   out_4695823766962492888[72] = 0;
   out_4695823766962492888[73] = 0;
   out_4695823766962492888[74] = 0;
   out_4695823766962492888[75] = 0;
   out_4695823766962492888[76] = 1;
   out_4695823766962492888[77] = 0;
   out_4695823766962492888[78] = 0;
   out_4695823766962492888[79] = 0;
   out_4695823766962492888[80] = 0;
   out_4695823766962492888[81] = 0;
   out_4695823766962492888[82] = 0;
   out_4695823766962492888[83] = 0;
   out_4695823766962492888[84] = 0;
   out_4695823766962492888[85] = dt;
   out_4695823766962492888[86] = 0;
   out_4695823766962492888[87] = 0;
   out_4695823766962492888[88] = 0;
   out_4695823766962492888[89] = 0;
   out_4695823766962492888[90] = 0;
   out_4695823766962492888[91] = 0;
   out_4695823766962492888[92] = 0;
   out_4695823766962492888[93] = 0;
   out_4695823766962492888[94] = 0;
   out_4695823766962492888[95] = 1;
   out_4695823766962492888[96] = 0;
   out_4695823766962492888[97] = 0;
   out_4695823766962492888[98] = 0;
   out_4695823766962492888[99] = 0;
   out_4695823766962492888[100] = 0;
   out_4695823766962492888[101] = 0;
   out_4695823766962492888[102] = 0;
   out_4695823766962492888[103] = 0;
   out_4695823766962492888[104] = dt;
   out_4695823766962492888[105] = 0;
   out_4695823766962492888[106] = 0;
   out_4695823766962492888[107] = 0;
   out_4695823766962492888[108] = 0;
   out_4695823766962492888[109] = 0;
   out_4695823766962492888[110] = 0;
   out_4695823766962492888[111] = 0;
   out_4695823766962492888[112] = 0;
   out_4695823766962492888[113] = 0;
   out_4695823766962492888[114] = 1;
   out_4695823766962492888[115] = 0;
   out_4695823766962492888[116] = 0;
   out_4695823766962492888[117] = 0;
   out_4695823766962492888[118] = 0;
   out_4695823766962492888[119] = 0;
   out_4695823766962492888[120] = 0;
   out_4695823766962492888[121] = 0;
   out_4695823766962492888[122] = 0;
   out_4695823766962492888[123] = 0;
   out_4695823766962492888[124] = 0;
   out_4695823766962492888[125] = 0;
   out_4695823766962492888[126] = 0;
   out_4695823766962492888[127] = 0;
   out_4695823766962492888[128] = 0;
   out_4695823766962492888[129] = 0;
   out_4695823766962492888[130] = 0;
   out_4695823766962492888[131] = 0;
   out_4695823766962492888[132] = 0;
   out_4695823766962492888[133] = 1;
   out_4695823766962492888[134] = 0;
   out_4695823766962492888[135] = 0;
   out_4695823766962492888[136] = 0;
   out_4695823766962492888[137] = 0;
   out_4695823766962492888[138] = 0;
   out_4695823766962492888[139] = 0;
   out_4695823766962492888[140] = 0;
   out_4695823766962492888[141] = 0;
   out_4695823766962492888[142] = 0;
   out_4695823766962492888[143] = 0;
   out_4695823766962492888[144] = 0;
   out_4695823766962492888[145] = 0;
   out_4695823766962492888[146] = 0;
   out_4695823766962492888[147] = 0;
   out_4695823766962492888[148] = 0;
   out_4695823766962492888[149] = 0;
   out_4695823766962492888[150] = 0;
   out_4695823766962492888[151] = 0;
   out_4695823766962492888[152] = 1;
   out_4695823766962492888[153] = 0;
   out_4695823766962492888[154] = 0;
   out_4695823766962492888[155] = 0;
   out_4695823766962492888[156] = 0;
   out_4695823766962492888[157] = 0;
   out_4695823766962492888[158] = 0;
   out_4695823766962492888[159] = 0;
   out_4695823766962492888[160] = 0;
   out_4695823766962492888[161] = 0;
   out_4695823766962492888[162] = 0;
   out_4695823766962492888[163] = 0;
   out_4695823766962492888[164] = 0;
   out_4695823766962492888[165] = 0;
   out_4695823766962492888[166] = 0;
   out_4695823766962492888[167] = 0;
   out_4695823766962492888[168] = 0;
   out_4695823766962492888[169] = 0;
   out_4695823766962492888[170] = 0;
   out_4695823766962492888[171] = 1;
   out_4695823766962492888[172] = 0;
   out_4695823766962492888[173] = 0;
   out_4695823766962492888[174] = 0;
   out_4695823766962492888[175] = 0;
   out_4695823766962492888[176] = 0;
   out_4695823766962492888[177] = 0;
   out_4695823766962492888[178] = 0;
   out_4695823766962492888[179] = 0;
   out_4695823766962492888[180] = 0;
   out_4695823766962492888[181] = 0;
   out_4695823766962492888[182] = 0;
   out_4695823766962492888[183] = 0;
   out_4695823766962492888[184] = 0;
   out_4695823766962492888[185] = 0;
   out_4695823766962492888[186] = 0;
   out_4695823766962492888[187] = 0;
   out_4695823766962492888[188] = 0;
   out_4695823766962492888[189] = 0;
   out_4695823766962492888[190] = 1;
   out_4695823766962492888[191] = 0;
   out_4695823766962492888[192] = 0;
   out_4695823766962492888[193] = 0;
   out_4695823766962492888[194] = 0;
   out_4695823766962492888[195] = 0;
   out_4695823766962492888[196] = 0;
   out_4695823766962492888[197] = 0;
   out_4695823766962492888[198] = 0;
   out_4695823766962492888[199] = 0;
   out_4695823766962492888[200] = 0;
   out_4695823766962492888[201] = 0;
   out_4695823766962492888[202] = 0;
   out_4695823766962492888[203] = 0;
   out_4695823766962492888[204] = 0;
   out_4695823766962492888[205] = 0;
   out_4695823766962492888[206] = 0;
   out_4695823766962492888[207] = 0;
   out_4695823766962492888[208] = 0;
   out_4695823766962492888[209] = 1;
   out_4695823766962492888[210] = 0;
   out_4695823766962492888[211] = 0;
   out_4695823766962492888[212] = 0;
   out_4695823766962492888[213] = 0;
   out_4695823766962492888[214] = 0;
   out_4695823766962492888[215] = 0;
   out_4695823766962492888[216] = 0;
   out_4695823766962492888[217] = 0;
   out_4695823766962492888[218] = 0;
   out_4695823766962492888[219] = 0;
   out_4695823766962492888[220] = 0;
   out_4695823766962492888[221] = 0;
   out_4695823766962492888[222] = 0;
   out_4695823766962492888[223] = 0;
   out_4695823766962492888[224] = 0;
   out_4695823766962492888[225] = 0;
   out_4695823766962492888[226] = 0;
   out_4695823766962492888[227] = 0;
   out_4695823766962492888[228] = 1;
   out_4695823766962492888[229] = 0;
   out_4695823766962492888[230] = 0;
   out_4695823766962492888[231] = 0;
   out_4695823766962492888[232] = 0;
   out_4695823766962492888[233] = 0;
   out_4695823766962492888[234] = 0;
   out_4695823766962492888[235] = 0;
   out_4695823766962492888[236] = 0;
   out_4695823766962492888[237] = 0;
   out_4695823766962492888[238] = 0;
   out_4695823766962492888[239] = 0;
   out_4695823766962492888[240] = 0;
   out_4695823766962492888[241] = 0;
   out_4695823766962492888[242] = 0;
   out_4695823766962492888[243] = 0;
   out_4695823766962492888[244] = 0;
   out_4695823766962492888[245] = 0;
   out_4695823766962492888[246] = 0;
   out_4695823766962492888[247] = 1;
   out_4695823766962492888[248] = 0;
   out_4695823766962492888[249] = 0;
   out_4695823766962492888[250] = 0;
   out_4695823766962492888[251] = 0;
   out_4695823766962492888[252] = 0;
   out_4695823766962492888[253] = 0;
   out_4695823766962492888[254] = 0;
   out_4695823766962492888[255] = 0;
   out_4695823766962492888[256] = 0;
   out_4695823766962492888[257] = 0;
   out_4695823766962492888[258] = 0;
   out_4695823766962492888[259] = 0;
   out_4695823766962492888[260] = 0;
   out_4695823766962492888[261] = 0;
   out_4695823766962492888[262] = 0;
   out_4695823766962492888[263] = 0;
   out_4695823766962492888[264] = 0;
   out_4695823766962492888[265] = 0;
   out_4695823766962492888[266] = 1;
   out_4695823766962492888[267] = 0;
   out_4695823766962492888[268] = 0;
   out_4695823766962492888[269] = 0;
   out_4695823766962492888[270] = 0;
   out_4695823766962492888[271] = 0;
   out_4695823766962492888[272] = 0;
   out_4695823766962492888[273] = 0;
   out_4695823766962492888[274] = 0;
   out_4695823766962492888[275] = 0;
   out_4695823766962492888[276] = 0;
   out_4695823766962492888[277] = 0;
   out_4695823766962492888[278] = 0;
   out_4695823766962492888[279] = 0;
   out_4695823766962492888[280] = 0;
   out_4695823766962492888[281] = 0;
   out_4695823766962492888[282] = 0;
   out_4695823766962492888[283] = 0;
   out_4695823766962492888[284] = 0;
   out_4695823766962492888[285] = 1;
   out_4695823766962492888[286] = 0;
   out_4695823766962492888[287] = 0;
   out_4695823766962492888[288] = 0;
   out_4695823766962492888[289] = 0;
   out_4695823766962492888[290] = 0;
   out_4695823766962492888[291] = 0;
   out_4695823766962492888[292] = 0;
   out_4695823766962492888[293] = 0;
   out_4695823766962492888[294] = 0;
   out_4695823766962492888[295] = 0;
   out_4695823766962492888[296] = 0;
   out_4695823766962492888[297] = 0;
   out_4695823766962492888[298] = 0;
   out_4695823766962492888[299] = 0;
   out_4695823766962492888[300] = 0;
   out_4695823766962492888[301] = 0;
   out_4695823766962492888[302] = 0;
   out_4695823766962492888[303] = 0;
   out_4695823766962492888[304] = 1;
   out_4695823766962492888[305] = 0;
   out_4695823766962492888[306] = 0;
   out_4695823766962492888[307] = 0;
   out_4695823766962492888[308] = 0;
   out_4695823766962492888[309] = 0;
   out_4695823766962492888[310] = 0;
   out_4695823766962492888[311] = 0;
   out_4695823766962492888[312] = 0;
   out_4695823766962492888[313] = 0;
   out_4695823766962492888[314] = 0;
   out_4695823766962492888[315] = 0;
   out_4695823766962492888[316] = 0;
   out_4695823766962492888[317] = 0;
   out_4695823766962492888[318] = 0;
   out_4695823766962492888[319] = 0;
   out_4695823766962492888[320] = 0;
   out_4695823766962492888[321] = 0;
   out_4695823766962492888[322] = 0;
   out_4695823766962492888[323] = 1;
}
void h_4(double *state, double *unused, double *out_2886213327032254372) {
   out_2886213327032254372[0] = state[6] + state[9];
   out_2886213327032254372[1] = state[7] + state[10];
   out_2886213327032254372[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_146496392957513442) {
   out_146496392957513442[0] = 0;
   out_146496392957513442[1] = 0;
   out_146496392957513442[2] = 0;
   out_146496392957513442[3] = 0;
   out_146496392957513442[4] = 0;
   out_146496392957513442[5] = 0;
   out_146496392957513442[6] = 1;
   out_146496392957513442[7] = 0;
   out_146496392957513442[8] = 0;
   out_146496392957513442[9] = 1;
   out_146496392957513442[10] = 0;
   out_146496392957513442[11] = 0;
   out_146496392957513442[12] = 0;
   out_146496392957513442[13] = 0;
   out_146496392957513442[14] = 0;
   out_146496392957513442[15] = 0;
   out_146496392957513442[16] = 0;
   out_146496392957513442[17] = 0;
   out_146496392957513442[18] = 0;
   out_146496392957513442[19] = 0;
   out_146496392957513442[20] = 0;
   out_146496392957513442[21] = 0;
   out_146496392957513442[22] = 0;
   out_146496392957513442[23] = 0;
   out_146496392957513442[24] = 0;
   out_146496392957513442[25] = 1;
   out_146496392957513442[26] = 0;
   out_146496392957513442[27] = 0;
   out_146496392957513442[28] = 1;
   out_146496392957513442[29] = 0;
   out_146496392957513442[30] = 0;
   out_146496392957513442[31] = 0;
   out_146496392957513442[32] = 0;
   out_146496392957513442[33] = 0;
   out_146496392957513442[34] = 0;
   out_146496392957513442[35] = 0;
   out_146496392957513442[36] = 0;
   out_146496392957513442[37] = 0;
   out_146496392957513442[38] = 0;
   out_146496392957513442[39] = 0;
   out_146496392957513442[40] = 0;
   out_146496392957513442[41] = 0;
   out_146496392957513442[42] = 0;
   out_146496392957513442[43] = 0;
   out_146496392957513442[44] = 1;
   out_146496392957513442[45] = 0;
   out_146496392957513442[46] = 0;
   out_146496392957513442[47] = 1;
   out_146496392957513442[48] = 0;
   out_146496392957513442[49] = 0;
   out_146496392957513442[50] = 0;
   out_146496392957513442[51] = 0;
   out_146496392957513442[52] = 0;
   out_146496392957513442[53] = 0;
}
void h_10(double *state, double *unused, double *out_1449862159655962354) {
   out_1449862159655962354[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1449862159655962354[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1449862159655962354[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3097566833981104856) {
   out_3097566833981104856[0] = 0;
   out_3097566833981104856[1] = 9.8100000000000005*cos(state[1]);
   out_3097566833981104856[2] = 0;
   out_3097566833981104856[3] = 0;
   out_3097566833981104856[4] = -state[8];
   out_3097566833981104856[5] = state[7];
   out_3097566833981104856[6] = 0;
   out_3097566833981104856[7] = state[5];
   out_3097566833981104856[8] = -state[4];
   out_3097566833981104856[9] = 0;
   out_3097566833981104856[10] = 0;
   out_3097566833981104856[11] = 0;
   out_3097566833981104856[12] = 1;
   out_3097566833981104856[13] = 0;
   out_3097566833981104856[14] = 0;
   out_3097566833981104856[15] = 1;
   out_3097566833981104856[16] = 0;
   out_3097566833981104856[17] = 0;
   out_3097566833981104856[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3097566833981104856[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3097566833981104856[20] = 0;
   out_3097566833981104856[21] = state[8];
   out_3097566833981104856[22] = 0;
   out_3097566833981104856[23] = -state[6];
   out_3097566833981104856[24] = -state[5];
   out_3097566833981104856[25] = 0;
   out_3097566833981104856[26] = state[3];
   out_3097566833981104856[27] = 0;
   out_3097566833981104856[28] = 0;
   out_3097566833981104856[29] = 0;
   out_3097566833981104856[30] = 0;
   out_3097566833981104856[31] = 1;
   out_3097566833981104856[32] = 0;
   out_3097566833981104856[33] = 0;
   out_3097566833981104856[34] = 1;
   out_3097566833981104856[35] = 0;
   out_3097566833981104856[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3097566833981104856[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3097566833981104856[38] = 0;
   out_3097566833981104856[39] = -state[7];
   out_3097566833981104856[40] = state[6];
   out_3097566833981104856[41] = 0;
   out_3097566833981104856[42] = state[4];
   out_3097566833981104856[43] = -state[3];
   out_3097566833981104856[44] = 0;
   out_3097566833981104856[45] = 0;
   out_3097566833981104856[46] = 0;
   out_3097566833981104856[47] = 0;
   out_3097566833981104856[48] = 0;
   out_3097566833981104856[49] = 0;
   out_3097566833981104856[50] = 1;
   out_3097566833981104856[51] = 0;
   out_3097566833981104856[52] = 0;
   out_3097566833981104856[53] = 1;
}
void h_13(double *state, double *unused, double *out_2970086023674538452) {
   out_2970086023674538452[0] = state[3];
   out_2970086023674538452[1] = state[4];
   out_2970086023674538452[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3065777432374819359) {
   out_3065777432374819359[0] = 0;
   out_3065777432374819359[1] = 0;
   out_3065777432374819359[2] = 0;
   out_3065777432374819359[3] = 1;
   out_3065777432374819359[4] = 0;
   out_3065777432374819359[5] = 0;
   out_3065777432374819359[6] = 0;
   out_3065777432374819359[7] = 0;
   out_3065777432374819359[8] = 0;
   out_3065777432374819359[9] = 0;
   out_3065777432374819359[10] = 0;
   out_3065777432374819359[11] = 0;
   out_3065777432374819359[12] = 0;
   out_3065777432374819359[13] = 0;
   out_3065777432374819359[14] = 0;
   out_3065777432374819359[15] = 0;
   out_3065777432374819359[16] = 0;
   out_3065777432374819359[17] = 0;
   out_3065777432374819359[18] = 0;
   out_3065777432374819359[19] = 0;
   out_3065777432374819359[20] = 0;
   out_3065777432374819359[21] = 0;
   out_3065777432374819359[22] = 1;
   out_3065777432374819359[23] = 0;
   out_3065777432374819359[24] = 0;
   out_3065777432374819359[25] = 0;
   out_3065777432374819359[26] = 0;
   out_3065777432374819359[27] = 0;
   out_3065777432374819359[28] = 0;
   out_3065777432374819359[29] = 0;
   out_3065777432374819359[30] = 0;
   out_3065777432374819359[31] = 0;
   out_3065777432374819359[32] = 0;
   out_3065777432374819359[33] = 0;
   out_3065777432374819359[34] = 0;
   out_3065777432374819359[35] = 0;
   out_3065777432374819359[36] = 0;
   out_3065777432374819359[37] = 0;
   out_3065777432374819359[38] = 0;
   out_3065777432374819359[39] = 0;
   out_3065777432374819359[40] = 0;
   out_3065777432374819359[41] = 1;
   out_3065777432374819359[42] = 0;
   out_3065777432374819359[43] = 0;
   out_3065777432374819359[44] = 0;
   out_3065777432374819359[45] = 0;
   out_3065777432374819359[46] = 0;
   out_3065777432374819359[47] = 0;
   out_3065777432374819359[48] = 0;
   out_3065777432374819359[49] = 0;
   out_3065777432374819359[50] = 0;
   out_3065777432374819359[51] = 0;
   out_3065777432374819359[52] = 0;
   out_3065777432374819359[53] = 0;
}
void h_14(double *state, double *unused, double *out_2307174073331940796) {
   out_2307174073331940796[0] = state[6];
   out_2307174073331940796[1] = state[7];
   out_2307174073331940796[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3816744463381971087) {
   out_3816744463381971087[0] = 0;
   out_3816744463381971087[1] = 0;
   out_3816744463381971087[2] = 0;
   out_3816744463381971087[3] = 0;
   out_3816744463381971087[4] = 0;
   out_3816744463381971087[5] = 0;
   out_3816744463381971087[6] = 1;
   out_3816744463381971087[7] = 0;
   out_3816744463381971087[8] = 0;
   out_3816744463381971087[9] = 0;
   out_3816744463381971087[10] = 0;
   out_3816744463381971087[11] = 0;
   out_3816744463381971087[12] = 0;
   out_3816744463381971087[13] = 0;
   out_3816744463381971087[14] = 0;
   out_3816744463381971087[15] = 0;
   out_3816744463381971087[16] = 0;
   out_3816744463381971087[17] = 0;
   out_3816744463381971087[18] = 0;
   out_3816744463381971087[19] = 0;
   out_3816744463381971087[20] = 0;
   out_3816744463381971087[21] = 0;
   out_3816744463381971087[22] = 0;
   out_3816744463381971087[23] = 0;
   out_3816744463381971087[24] = 0;
   out_3816744463381971087[25] = 1;
   out_3816744463381971087[26] = 0;
   out_3816744463381971087[27] = 0;
   out_3816744463381971087[28] = 0;
   out_3816744463381971087[29] = 0;
   out_3816744463381971087[30] = 0;
   out_3816744463381971087[31] = 0;
   out_3816744463381971087[32] = 0;
   out_3816744463381971087[33] = 0;
   out_3816744463381971087[34] = 0;
   out_3816744463381971087[35] = 0;
   out_3816744463381971087[36] = 0;
   out_3816744463381971087[37] = 0;
   out_3816744463381971087[38] = 0;
   out_3816744463381971087[39] = 0;
   out_3816744463381971087[40] = 0;
   out_3816744463381971087[41] = 0;
   out_3816744463381971087[42] = 0;
   out_3816744463381971087[43] = 0;
   out_3816744463381971087[44] = 1;
   out_3816744463381971087[45] = 0;
   out_3816744463381971087[46] = 0;
   out_3816744463381971087[47] = 0;
   out_3816744463381971087[48] = 0;
   out_3816744463381971087[49] = 0;
   out_3816744463381971087[50] = 0;
   out_3816744463381971087[51] = 0;
   out_3816744463381971087[52] = 0;
   out_3816744463381971087[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3009922513179117509) {
  err_fun(nom_x, delta_x, out_3009922513179117509);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_975857412122476284) {
  inv_err_fun(nom_x, true_x, out_975857412122476284);
}
void pose_H_mod_fun(double *state, double *out_5701585413794445279) {
  H_mod_fun(state, out_5701585413794445279);
}
void pose_f_fun(double *state, double dt, double *out_7100436431164388549) {
  f_fun(state,  dt, out_7100436431164388549);
}
void pose_F_fun(double *state, double dt, double *out_4695823766962492888) {
  F_fun(state,  dt, out_4695823766962492888);
}
void pose_h_4(double *state, double *unused, double *out_2886213327032254372) {
  h_4(state, unused, out_2886213327032254372);
}
void pose_H_4(double *state, double *unused, double *out_146496392957513442) {
  H_4(state, unused, out_146496392957513442);
}
void pose_h_10(double *state, double *unused, double *out_1449862159655962354) {
  h_10(state, unused, out_1449862159655962354);
}
void pose_H_10(double *state, double *unused, double *out_3097566833981104856) {
  H_10(state, unused, out_3097566833981104856);
}
void pose_h_13(double *state, double *unused, double *out_2970086023674538452) {
  h_13(state, unused, out_2970086023674538452);
}
void pose_H_13(double *state, double *unused, double *out_3065777432374819359) {
  H_13(state, unused, out_3065777432374819359);
}
void pose_h_14(double *state, double *unused, double *out_2307174073331940796) {
  h_14(state, unused, out_2307174073331940796);
}
void pose_H_14(double *state, double *unused, double *out_3816744463381971087) {
  H_14(state, unused, out_3816744463381971087);
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
