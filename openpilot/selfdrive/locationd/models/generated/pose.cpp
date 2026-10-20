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
void err_fun(double *nom_x, double *delta_x, double *out_7083554587370275014) {
   out_7083554587370275014[0] = delta_x[0] + nom_x[0];
   out_7083554587370275014[1] = delta_x[1] + nom_x[1];
   out_7083554587370275014[2] = delta_x[2] + nom_x[2];
   out_7083554587370275014[3] = delta_x[3] + nom_x[3];
   out_7083554587370275014[4] = delta_x[4] + nom_x[4];
   out_7083554587370275014[5] = delta_x[5] + nom_x[5];
   out_7083554587370275014[6] = delta_x[6] + nom_x[6];
   out_7083554587370275014[7] = delta_x[7] + nom_x[7];
   out_7083554587370275014[8] = delta_x[8] + nom_x[8];
   out_7083554587370275014[9] = delta_x[9] + nom_x[9];
   out_7083554587370275014[10] = delta_x[10] + nom_x[10];
   out_7083554587370275014[11] = delta_x[11] + nom_x[11];
   out_7083554587370275014[12] = delta_x[12] + nom_x[12];
   out_7083554587370275014[13] = delta_x[13] + nom_x[13];
   out_7083554587370275014[14] = delta_x[14] + nom_x[14];
   out_7083554587370275014[15] = delta_x[15] + nom_x[15];
   out_7083554587370275014[16] = delta_x[16] + nom_x[16];
   out_7083554587370275014[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6548503546481104197) {
   out_6548503546481104197[0] = -nom_x[0] + true_x[0];
   out_6548503546481104197[1] = -nom_x[1] + true_x[1];
   out_6548503546481104197[2] = -nom_x[2] + true_x[2];
   out_6548503546481104197[3] = -nom_x[3] + true_x[3];
   out_6548503546481104197[4] = -nom_x[4] + true_x[4];
   out_6548503546481104197[5] = -nom_x[5] + true_x[5];
   out_6548503546481104197[6] = -nom_x[6] + true_x[6];
   out_6548503546481104197[7] = -nom_x[7] + true_x[7];
   out_6548503546481104197[8] = -nom_x[8] + true_x[8];
   out_6548503546481104197[9] = -nom_x[9] + true_x[9];
   out_6548503546481104197[10] = -nom_x[10] + true_x[10];
   out_6548503546481104197[11] = -nom_x[11] + true_x[11];
   out_6548503546481104197[12] = -nom_x[12] + true_x[12];
   out_6548503546481104197[13] = -nom_x[13] + true_x[13];
   out_6548503546481104197[14] = -nom_x[14] + true_x[14];
   out_6548503546481104197[15] = -nom_x[15] + true_x[15];
   out_6548503546481104197[16] = -nom_x[16] + true_x[16];
   out_6548503546481104197[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8484867830328864601) {
   out_8484867830328864601[0] = 1.0;
   out_8484867830328864601[1] = 0.0;
   out_8484867830328864601[2] = 0.0;
   out_8484867830328864601[3] = 0.0;
   out_8484867830328864601[4] = 0.0;
   out_8484867830328864601[5] = 0.0;
   out_8484867830328864601[6] = 0.0;
   out_8484867830328864601[7] = 0.0;
   out_8484867830328864601[8] = 0.0;
   out_8484867830328864601[9] = 0.0;
   out_8484867830328864601[10] = 0.0;
   out_8484867830328864601[11] = 0.0;
   out_8484867830328864601[12] = 0.0;
   out_8484867830328864601[13] = 0.0;
   out_8484867830328864601[14] = 0.0;
   out_8484867830328864601[15] = 0.0;
   out_8484867830328864601[16] = 0.0;
   out_8484867830328864601[17] = 0.0;
   out_8484867830328864601[18] = 0.0;
   out_8484867830328864601[19] = 1.0;
   out_8484867830328864601[20] = 0.0;
   out_8484867830328864601[21] = 0.0;
   out_8484867830328864601[22] = 0.0;
   out_8484867830328864601[23] = 0.0;
   out_8484867830328864601[24] = 0.0;
   out_8484867830328864601[25] = 0.0;
   out_8484867830328864601[26] = 0.0;
   out_8484867830328864601[27] = 0.0;
   out_8484867830328864601[28] = 0.0;
   out_8484867830328864601[29] = 0.0;
   out_8484867830328864601[30] = 0.0;
   out_8484867830328864601[31] = 0.0;
   out_8484867830328864601[32] = 0.0;
   out_8484867830328864601[33] = 0.0;
   out_8484867830328864601[34] = 0.0;
   out_8484867830328864601[35] = 0.0;
   out_8484867830328864601[36] = 0.0;
   out_8484867830328864601[37] = 0.0;
   out_8484867830328864601[38] = 1.0;
   out_8484867830328864601[39] = 0.0;
   out_8484867830328864601[40] = 0.0;
   out_8484867830328864601[41] = 0.0;
   out_8484867830328864601[42] = 0.0;
   out_8484867830328864601[43] = 0.0;
   out_8484867830328864601[44] = 0.0;
   out_8484867830328864601[45] = 0.0;
   out_8484867830328864601[46] = 0.0;
   out_8484867830328864601[47] = 0.0;
   out_8484867830328864601[48] = 0.0;
   out_8484867830328864601[49] = 0.0;
   out_8484867830328864601[50] = 0.0;
   out_8484867830328864601[51] = 0.0;
   out_8484867830328864601[52] = 0.0;
   out_8484867830328864601[53] = 0.0;
   out_8484867830328864601[54] = 0.0;
   out_8484867830328864601[55] = 0.0;
   out_8484867830328864601[56] = 0.0;
   out_8484867830328864601[57] = 1.0;
   out_8484867830328864601[58] = 0.0;
   out_8484867830328864601[59] = 0.0;
   out_8484867830328864601[60] = 0.0;
   out_8484867830328864601[61] = 0.0;
   out_8484867830328864601[62] = 0.0;
   out_8484867830328864601[63] = 0.0;
   out_8484867830328864601[64] = 0.0;
   out_8484867830328864601[65] = 0.0;
   out_8484867830328864601[66] = 0.0;
   out_8484867830328864601[67] = 0.0;
   out_8484867830328864601[68] = 0.0;
   out_8484867830328864601[69] = 0.0;
   out_8484867830328864601[70] = 0.0;
   out_8484867830328864601[71] = 0.0;
   out_8484867830328864601[72] = 0.0;
   out_8484867830328864601[73] = 0.0;
   out_8484867830328864601[74] = 0.0;
   out_8484867830328864601[75] = 0.0;
   out_8484867830328864601[76] = 1.0;
   out_8484867830328864601[77] = 0.0;
   out_8484867830328864601[78] = 0.0;
   out_8484867830328864601[79] = 0.0;
   out_8484867830328864601[80] = 0.0;
   out_8484867830328864601[81] = 0.0;
   out_8484867830328864601[82] = 0.0;
   out_8484867830328864601[83] = 0.0;
   out_8484867830328864601[84] = 0.0;
   out_8484867830328864601[85] = 0.0;
   out_8484867830328864601[86] = 0.0;
   out_8484867830328864601[87] = 0.0;
   out_8484867830328864601[88] = 0.0;
   out_8484867830328864601[89] = 0.0;
   out_8484867830328864601[90] = 0.0;
   out_8484867830328864601[91] = 0.0;
   out_8484867830328864601[92] = 0.0;
   out_8484867830328864601[93] = 0.0;
   out_8484867830328864601[94] = 0.0;
   out_8484867830328864601[95] = 1.0;
   out_8484867830328864601[96] = 0.0;
   out_8484867830328864601[97] = 0.0;
   out_8484867830328864601[98] = 0.0;
   out_8484867830328864601[99] = 0.0;
   out_8484867830328864601[100] = 0.0;
   out_8484867830328864601[101] = 0.0;
   out_8484867830328864601[102] = 0.0;
   out_8484867830328864601[103] = 0.0;
   out_8484867830328864601[104] = 0.0;
   out_8484867830328864601[105] = 0.0;
   out_8484867830328864601[106] = 0.0;
   out_8484867830328864601[107] = 0.0;
   out_8484867830328864601[108] = 0.0;
   out_8484867830328864601[109] = 0.0;
   out_8484867830328864601[110] = 0.0;
   out_8484867830328864601[111] = 0.0;
   out_8484867830328864601[112] = 0.0;
   out_8484867830328864601[113] = 0.0;
   out_8484867830328864601[114] = 1.0;
   out_8484867830328864601[115] = 0.0;
   out_8484867830328864601[116] = 0.0;
   out_8484867830328864601[117] = 0.0;
   out_8484867830328864601[118] = 0.0;
   out_8484867830328864601[119] = 0.0;
   out_8484867830328864601[120] = 0.0;
   out_8484867830328864601[121] = 0.0;
   out_8484867830328864601[122] = 0.0;
   out_8484867830328864601[123] = 0.0;
   out_8484867830328864601[124] = 0.0;
   out_8484867830328864601[125] = 0.0;
   out_8484867830328864601[126] = 0.0;
   out_8484867830328864601[127] = 0.0;
   out_8484867830328864601[128] = 0.0;
   out_8484867830328864601[129] = 0.0;
   out_8484867830328864601[130] = 0.0;
   out_8484867830328864601[131] = 0.0;
   out_8484867830328864601[132] = 0.0;
   out_8484867830328864601[133] = 1.0;
   out_8484867830328864601[134] = 0.0;
   out_8484867830328864601[135] = 0.0;
   out_8484867830328864601[136] = 0.0;
   out_8484867830328864601[137] = 0.0;
   out_8484867830328864601[138] = 0.0;
   out_8484867830328864601[139] = 0.0;
   out_8484867830328864601[140] = 0.0;
   out_8484867830328864601[141] = 0.0;
   out_8484867830328864601[142] = 0.0;
   out_8484867830328864601[143] = 0.0;
   out_8484867830328864601[144] = 0.0;
   out_8484867830328864601[145] = 0.0;
   out_8484867830328864601[146] = 0.0;
   out_8484867830328864601[147] = 0.0;
   out_8484867830328864601[148] = 0.0;
   out_8484867830328864601[149] = 0.0;
   out_8484867830328864601[150] = 0.0;
   out_8484867830328864601[151] = 0.0;
   out_8484867830328864601[152] = 1.0;
   out_8484867830328864601[153] = 0.0;
   out_8484867830328864601[154] = 0.0;
   out_8484867830328864601[155] = 0.0;
   out_8484867830328864601[156] = 0.0;
   out_8484867830328864601[157] = 0.0;
   out_8484867830328864601[158] = 0.0;
   out_8484867830328864601[159] = 0.0;
   out_8484867830328864601[160] = 0.0;
   out_8484867830328864601[161] = 0.0;
   out_8484867830328864601[162] = 0.0;
   out_8484867830328864601[163] = 0.0;
   out_8484867830328864601[164] = 0.0;
   out_8484867830328864601[165] = 0.0;
   out_8484867830328864601[166] = 0.0;
   out_8484867830328864601[167] = 0.0;
   out_8484867830328864601[168] = 0.0;
   out_8484867830328864601[169] = 0.0;
   out_8484867830328864601[170] = 0.0;
   out_8484867830328864601[171] = 1.0;
   out_8484867830328864601[172] = 0.0;
   out_8484867830328864601[173] = 0.0;
   out_8484867830328864601[174] = 0.0;
   out_8484867830328864601[175] = 0.0;
   out_8484867830328864601[176] = 0.0;
   out_8484867830328864601[177] = 0.0;
   out_8484867830328864601[178] = 0.0;
   out_8484867830328864601[179] = 0.0;
   out_8484867830328864601[180] = 0.0;
   out_8484867830328864601[181] = 0.0;
   out_8484867830328864601[182] = 0.0;
   out_8484867830328864601[183] = 0.0;
   out_8484867830328864601[184] = 0.0;
   out_8484867830328864601[185] = 0.0;
   out_8484867830328864601[186] = 0.0;
   out_8484867830328864601[187] = 0.0;
   out_8484867830328864601[188] = 0.0;
   out_8484867830328864601[189] = 0.0;
   out_8484867830328864601[190] = 1.0;
   out_8484867830328864601[191] = 0.0;
   out_8484867830328864601[192] = 0.0;
   out_8484867830328864601[193] = 0.0;
   out_8484867830328864601[194] = 0.0;
   out_8484867830328864601[195] = 0.0;
   out_8484867830328864601[196] = 0.0;
   out_8484867830328864601[197] = 0.0;
   out_8484867830328864601[198] = 0.0;
   out_8484867830328864601[199] = 0.0;
   out_8484867830328864601[200] = 0.0;
   out_8484867830328864601[201] = 0.0;
   out_8484867830328864601[202] = 0.0;
   out_8484867830328864601[203] = 0.0;
   out_8484867830328864601[204] = 0.0;
   out_8484867830328864601[205] = 0.0;
   out_8484867830328864601[206] = 0.0;
   out_8484867830328864601[207] = 0.0;
   out_8484867830328864601[208] = 0.0;
   out_8484867830328864601[209] = 1.0;
   out_8484867830328864601[210] = 0.0;
   out_8484867830328864601[211] = 0.0;
   out_8484867830328864601[212] = 0.0;
   out_8484867830328864601[213] = 0.0;
   out_8484867830328864601[214] = 0.0;
   out_8484867830328864601[215] = 0.0;
   out_8484867830328864601[216] = 0.0;
   out_8484867830328864601[217] = 0.0;
   out_8484867830328864601[218] = 0.0;
   out_8484867830328864601[219] = 0.0;
   out_8484867830328864601[220] = 0.0;
   out_8484867830328864601[221] = 0.0;
   out_8484867830328864601[222] = 0.0;
   out_8484867830328864601[223] = 0.0;
   out_8484867830328864601[224] = 0.0;
   out_8484867830328864601[225] = 0.0;
   out_8484867830328864601[226] = 0.0;
   out_8484867830328864601[227] = 0.0;
   out_8484867830328864601[228] = 1.0;
   out_8484867830328864601[229] = 0.0;
   out_8484867830328864601[230] = 0.0;
   out_8484867830328864601[231] = 0.0;
   out_8484867830328864601[232] = 0.0;
   out_8484867830328864601[233] = 0.0;
   out_8484867830328864601[234] = 0.0;
   out_8484867830328864601[235] = 0.0;
   out_8484867830328864601[236] = 0.0;
   out_8484867830328864601[237] = 0.0;
   out_8484867830328864601[238] = 0.0;
   out_8484867830328864601[239] = 0.0;
   out_8484867830328864601[240] = 0.0;
   out_8484867830328864601[241] = 0.0;
   out_8484867830328864601[242] = 0.0;
   out_8484867830328864601[243] = 0.0;
   out_8484867830328864601[244] = 0.0;
   out_8484867830328864601[245] = 0.0;
   out_8484867830328864601[246] = 0.0;
   out_8484867830328864601[247] = 1.0;
   out_8484867830328864601[248] = 0.0;
   out_8484867830328864601[249] = 0.0;
   out_8484867830328864601[250] = 0.0;
   out_8484867830328864601[251] = 0.0;
   out_8484867830328864601[252] = 0.0;
   out_8484867830328864601[253] = 0.0;
   out_8484867830328864601[254] = 0.0;
   out_8484867830328864601[255] = 0.0;
   out_8484867830328864601[256] = 0.0;
   out_8484867830328864601[257] = 0.0;
   out_8484867830328864601[258] = 0.0;
   out_8484867830328864601[259] = 0.0;
   out_8484867830328864601[260] = 0.0;
   out_8484867830328864601[261] = 0.0;
   out_8484867830328864601[262] = 0.0;
   out_8484867830328864601[263] = 0.0;
   out_8484867830328864601[264] = 0.0;
   out_8484867830328864601[265] = 0.0;
   out_8484867830328864601[266] = 1.0;
   out_8484867830328864601[267] = 0.0;
   out_8484867830328864601[268] = 0.0;
   out_8484867830328864601[269] = 0.0;
   out_8484867830328864601[270] = 0.0;
   out_8484867830328864601[271] = 0.0;
   out_8484867830328864601[272] = 0.0;
   out_8484867830328864601[273] = 0.0;
   out_8484867830328864601[274] = 0.0;
   out_8484867830328864601[275] = 0.0;
   out_8484867830328864601[276] = 0.0;
   out_8484867830328864601[277] = 0.0;
   out_8484867830328864601[278] = 0.0;
   out_8484867830328864601[279] = 0.0;
   out_8484867830328864601[280] = 0.0;
   out_8484867830328864601[281] = 0.0;
   out_8484867830328864601[282] = 0.0;
   out_8484867830328864601[283] = 0.0;
   out_8484867830328864601[284] = 0.0;
   out_8484867830328864601[285] = 1.0;
   out_8484867830328864601[286] = 0.0;
   out_8484867830328864601[287] = 0.0;
   out_8484867830328864601[288] = 0.0;
   out_8484867830328864601[289] = 0.0;
   out_8484867830328864601[290] = 0.0;
   out_8484867830328864601[291] = 0.0;
   out_8484867830328864601[292] = 0.0;
   out_8484867830328864601[293] = 0.0;
   out_8484867830328864601[294] = 0.0;
   out_8484867830328864601[295] = 0.0;
   out_8484867830328864601[296] = 0.0;
   out_8484867830328864601[297] = 0.0;
   out_8484867830328864601[298] = 0.0;
   out_8484867830328864601[299] = 0.0;
   out_8484867830328864601[300] = 0.0;
   out_8484867830328864601[301] = 0.0;
   out_8484867830328864601[302] = 0.0;
   out_8484867830328864601[303] = 0.0;
   out_8484867830328864601[304] = 1.0;
   out_8484867830328864601[305] = 0.0;
   out_8484867830328864601[306] = 0.0;
   out_8484867830328864601[307] = 0.0;
   out_8484867830328864601[308] = 0.0;
   out_8484867830328864601[309] = 0.0;
   out_8484867830328864601[310] = 0.0;
   out_8484867830328864601[311] = 0.0;
   out_8484867830328864601[312] = 0.0;
   out_8484867830328864601[313] = 0.0;
   out_8484867830328864601[314] = 0.0;
   out_8484867830328864601[315] = 0.0;
   out_8484867830328864601[316] = 0.0;
   out_8484867830328864601[317] = 0.0;
   out_8484867830328864601[318] = 0.0;
   out_8484867830328864601[319] = 0.0;
   out_8484867830328864601[320] = 0.0;
   out_8484867830328864601[321] = 0.0;
   out_8484867830328864601[322] = 0.0;
   out_8484867830328864601[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6058628880177520660) {
   out_6058628880177520660[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6058628880177520660[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6058628880177520660[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6058628880177520660[3] = dt*state[12] + state[3];
   out_6058628880177520660[4] = dt*state[13] + state[4];
   out_6058628880177520660[5] = dt*state[14] + state[5];
   out_6058628880177520660[6] = state[6];
   out_6058628880177520660[7] = state[7];
   out_6058628880177520660[8] = state[8];
   out_6058628880177520660[9] = state[9];
   out_6058628880177520660[10] = state[10];
   out_6058628880177520660[11] = state[11];
   out_6058628880177520660[12] = state[12];
   out_6058628880177520660[13] = state[13];
   out_6058628880177520660[14] = state[14];
   out_6058628880177520660[15] = state[15];
   out_6058628880177520660[16] = state[16];
   out_6058628880177520660[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5197906072130444471) {
   out_5197906072130444471[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5197906072130444471[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5197906072130444471[2] = 0;
   out_5197906072130444471[3] = 0;
   out_5197906072130444471[4] = 0;
   out_5197906072130444471[5] = 0;
   out_5197906072130444471[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5197906072130444471[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5197906072130444471[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5197906072130444471[9] = 0;
   out_5197906072130444471[10] = 0;
   out_5197906072130444471[11] = 0;
   out_5197906072130444471[12] = 0;
   out_5197906072130444471[13] = 0;
   out_5197906072130444471[14] = 0;
   out_5197906072130444471[15] = 0;
   out_5197906072130444471[16] = 0;
   out_5197906072130444471[17] = 0;
   out_5197906072130444471[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5197906072130444471[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5197906072130444471[20] = 0;
   out_5197906072130444471[21] = 0;
   out_5197906072130444471[22] = 0;
   out_5197906072130444471[23] = 0;
   out_5197906072130444471[24] = 0;
   out_5197906072130444471[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5197906072130444471[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5197906072130444471[27] = 0;
   out_5197906072130444471[28] = 0;
   out_5197906072130444471[29] = 0;
   out_5197906072130444471[30] = 0;
   out_5197906072130444471[31] = 0;
   out_5197906072130444471[32] = 0;
   out_5197906072130444471[33] = 0;
   out_5197906072130444471[34] = 0;
   out_5197906072130444471[35] = 0;
   out_5197906072130444471[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5197906072130444471[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5197906072130444471[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5197906072130444471[39] = 0;
   out_5197906072130444471[40] = 0;
   out_5197906072130444471[41] = 0;
   out_5197906072130444471[42] = 0;
   out_5197906072130444471[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5197906072130444471[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5197906072130444471[45] = 0;
   out_5197906072130444471[46] = 0;
   out_5197906072130444471[47] = 0;
   out_5197906072130444471[48] = 0;
   out_5197906072130444471[49] = 0;
   out_5197906072130444471[50] = 0;
   out_5197906072130444471[51] = 0;
   out_5197906072130444471[52] = 0;
   out_5197906072130444471[53] = 0;
   out_5197906072130444471[54] = 0;
   out_5197906072130444471[55] = 0;
   out_5197906072130444471[56] = 0;
   out_5197906072130444471[57] = 1;
   out_5197906072130444471[58] = 0;
   out_5197906072130444471[59] = 0;
   out_5197906072130444471[60] = 0;
   out_5197906072130444471[61] = 0;
   out_5197906072130444471[62] = 0;
   out_5197906072130444471[63] = 0;
   out_5197906072130444471[64] = 0;
   out_5197906072130444471[65] = 0;
   out_5197906072130444471[66] = dt;
   out_5197906072130444471[67] = 0;
   out_5197906072130444471[68] = 0;
   out_5197906072130444471[69] = 0;
   out_5197906072130444471[70] = 0;
   out_5197906072130444471[71] = 0;
   out_5197906072130444471[72] = 0;
   out_5197906072130444471[73] = 0;
   out_5197906072130444471[74] = 0;
   out_5197906072130444471[75] = 0;
   out_5197906072130444471[76] = 1;
   out_5197906072130444471[77] = 0;
   out_5197906072130444471[78] = 0;
   out_5197906072130444471[79] = 0;
   out_5197906072130444471[80] = 0;
   out_5197906072130444471[81] = 0;
   out_5197906072130444471[82] = 0;
   out_5197906072130444471[83] = 0;
   out_5197906072130444471[84] = 0;
   out_5197906072130444471[85] = dt;
   out_5197906072130444471[86] = 0;
   out_5197906072130444471[87] = 0;
   out_5197906072130444471[88] = 0;
   out_5197906072130444471[89] = 0;
   out_5197906072130444471[90] = 0;
   out_5197906072130444471[91] = 0;
   out_5197906072130444471[92] = 0;
   out_5197906072130444471[93] = 0;
   out_5197906072130444471[94] = 0;
   out_5197906072130444471[95] = 1;
   out_5197906072130444471[96] = 0;
   out_5197906072130444471[97] = 0;
   out_5197906072130444471[98] = 0;
   out_5197906072130444471[99] = 0;
   out_5197906072130444471[100] = 0;
   out_5197906072130444471[101] = 0;
   out_5197906072130444471[102] = 0;
   out_5197906072130444471[103] = 0;
   out_5197906072130444471[104] = dt;
   out_5197906072130444471[105] = 0;
   out_5197906072130444471[106] = 0;
   out_5197906072130444471[107] = 0;
   out_5197906072130444471[108] = 0;
   out_5197906072130444471[109] = 0;
   out_5197906072130444471[110] = 0;
   out_5197906072130444471[111] = 0;
   out_5197906072130444471[112] = 0;
   out_5197906072130444471[113] = 0;
   out_5197906072130444471[114] = 1;
   out_5197906072130444471[115] = 0;
   out_5197906072130444471[116] = 0;
   out_5197906072130444471[117] = 0;
   out_5197906072130444471[118] = 0;
   out_5197906072130444471[119] = 0;
   out_5197906072130444471[120] = 0;
   out_5197906072130444471[121] = 0;
   out_5197906072130444471[122] = 0;
   out_5197906072130444471[123] = 0;
   out_5197906072130444471[124] = 0;
   out_5197906072130444471[125] = 0;
   out_5197906072130444471[126] = 0;
   out_5197906072130444471[127] = 0;
   out_5197906072130444471[128] = 0;
   out_5197906072130444471[129] = 0;
   out_5197906072130444471[130] = 0;
   out_5197906072130444471[131] = 0;
   out_5197906072130444471[132] = 0;
   out_5197906072130444471[133] = 1;
   out_5197906072130444471[134] = 0;
   out_5197906072130444471[135] = 0;
   out_5197906072130444471[136] = 0;
   out_5197906072130444471[137] = 0;
   out_5197906072130444471[138] = 0;
   out_5197906072130444471[139] = 0;
   out_5197906072130444471[140] = 0;
   out_5197906072130444471[141] = 0;
   out_5197906072130444471[142] = 0;
   out_5197906072130444471[143] = 0;
   out_5197906072130444471[144] = 0;
   out_5197906072130444471[145] = 0;
   out_5197906072130444471[146] = 0;
   out_5197906072130444471[147] = 0;
   out_5197906072130444471[148] = 0;
   out_5197906072130444471[149] = 0;
   out_5197906072130444471[150] = 0;
   out_5197906072130444471[151] = 0;
   out_5197906072130444471[152] = 1;
   out_5197906072130444471[153] = 0;
   out_5197906072130444471[154] = 0;
   out_5197906072130444471[155] = 0;
   out_5197906072130444471[156] = 0;
   out_5197906072130444471[157] = 0;
   out_5197906072130444471[158] = 0;
   out_5197906072130444471[159] = 0;
   out_5197906072130444471[160] = 0;
   out_5197906072130444471[161] = 0;
   out_5197906072130444471[162] = 0;
   out_5197906072130444471[163] = 0;
   out_5197906072130444471[164] = 0;
   out_5197906072130444471[165] = 0;
   out_5197906072130444471[166] = 0;
   out_5197906072130444471[167] = 0;
   out_5197906072130444471[168] = 0;
   out_5197906072130444471[169] = 0;
   out_5197906072130444471[170] = 0;
   out_5197906072130444471[171] = 1;
   out_5197906072130444471[172] = 0;
   out_5197906072130444471[173] = 0;
   out_5197906072130444471[174] = 0;
   out_5197906072130444471[175] = 0;
   out_5197906072130444471[176] = 0;
   out_5197906072130444471[177] = 0;
   out_5197906072130444471[178] = 0;
   out_5197906072130444471[179] = 0;
   out_5197906072130444471[180] = 0;
   out_5197906072130444471[181] = 0;
   out_5197906072130444471[182] = 0;
   out_5197906072130444471[183] = 0;
   out_5197906072130444471[184] = 0;
   out_5197906072130444471[185] = 0;
   out_5197906072130444471[186] = 0;
   out_5197906072130444471[187] = 0;
   out_5197906072130444471[188] = 0;
   out_5197906072130444471[189] = 0;
   out_5197906072130444471[190] = 1;
   out_5197906072130444471[191] = 0;
   out_5197906072130444471[192] = 0;
   out_5197906072130444471[193] = 0;
   out_5197906072130444471[194] = 0;
   out_5197906072130444471[195] = 0;
   out_5197906072130444471[196] = 0;
   out_5197906072130444471[197] = 0;
   out_5197906072130444471[198] = 0;
   out_5197906072130444471[199] = 0;
   out_5197906072130444471[200] = 0;
   out_5197906072130444471[201] = 0;
   out_5197906072130444471[202] = 0;
   out_5197906072130444471[203] = 0;
   out_5197906072130444471[204] = 0;
   out_5197906072130444471[205] = 0;
   out_5197906072130444471[206] = 0;
   out_5197906072130444471[207] = 0;
   out_5197906072130444471[208] = 0;
   out_5197906072130444471[209] = 1;
   out_5197906072130444471[210] = 0;
   out_5197906072130444471[211] = 0;
   out_5197906072130444471[212] = 0;
   out_5197906072130444471[213] = 0;
   out_5197906072130444471[214] = 0;
   out_5197906072130444471[215] = 0;
   out_5197906072130444471[216] = 0;
   out_5197906072130444471[217] = 0;
   out_5197906072130444471[218] = 0;
   out_5197906072130444471[219] = 0;
   out_5197906072130444471[220] = 0;
   out_5197906072130444471[221] = 0;
   out_5197906072130444471[222] = 0;
   out_5197906072130444471[223] = 0;
   out_5197906072130444471[224] = 0;
   out_5197906072130444471[225] = 0;
   out_5197906072130444471[226] = 0;
   out_5197906072130444471[227] = 0;
   out_5197906072130444471[228] = 1;
   out_5197906072130444471[229] = 0;
   out_5197906072130444471[230] = 0;
   out_5197906072130444471[231] = 0;
   out_5197906072130444471[232] = 0;
   out_5197906072130444471[233] = 0;
   out_5197906072130444471[234] = 0;
   out_5197906072130444471[235] = 0;
   out_5197906072130444471[236] = 0;
   out_5197906072130444471[237] = 0;
   out_5197906072130444471[238] = 0;
   out_5197906072130444471[239] = 0;
   out_5197906072130444471[240] = 0;
   out_5197906072130444471[241] = 0;
   out_5197906072130444471[242] = 0;
   out_5197906072130444471[243] = 0;
   out_5197906072130444471[244] = 0;
   out_5197906072130444471[245] = 0;
   out_5197906072130444471[246] = 0;
   out_5197906072130444471[247] = 1;
   out_5197906072130444471[248] = 0;
   out_5197906072130444471[249] = 0;
   out_5197906072130444471[250] = 0;
   out_5197906072130444471[251] = 0;
   out_5197906072130444471[252] = 0;
   out_5197906072130444471[253] = 0;
   out_5197906072130444471[254] = 0;
   out_5197906072130444471[255] = 0;
   out_5197906072130444471[256] = 0;
   out_5197906072130444471[257] = 0;
   out_5197906072130444471[258] = 0;
   out_5197906072130444471[259] = 0;
   out_5197906072130444471[260] = 0;
   out_5197906072130444471[261] = 0;
   out_5197906072130444471[262] = 0;
   out_5197906072130444471[263] = 0;
   out_5197906072130444471[264] = 0;
   out_5197906072130444471[265] = 0;
   out_5197906072130444471[266] = 1;
   out_5197906072130444471[267] = 0;
   out_5197906072130444471[268] = 0;
   out_5197906072130444471[269] = 0;
   out_5197906072130444471[270] = 0;
   out_5197906072130444471[271] = 0;
   out_5197906072130444471[272] = 0;
   out_5197906072130444471[273] = 0;
   out_5197906072130444471[274] = 0;
   out_5197906072130444471[275] = 0;
   out_5197906072130444471[276] = 0;
   out_5197906072130444471[277] = 0;
   out_5197906072130444471[278] = 0;
   out_5197906072130444471[279] = 0;
   out_5197906072130444471[280] = 0;
   out_5197906072130444471[281] = 0;
   out_5197906072130444471[282] = 0;
   out_5197906072130444471[283] = 0;
   out_5197906072130444471[284] = 0;
   out_5197906072130444471[285] = 1;
   out_5197906072130444471[286] = 0;
   out_5197906072130444471[287] = 0;
   out_5197906072130444471[288] = 0;
   out_5197906072130444471[289] = 0;
   out_5197906072130444471[290] = 0;
   out_5197906072130444471[291] = 0;
   out_5197906072130444471[292] = 0;
   out_5197906072130444471[293] = 0;
   out_5197906072130444471[294] = 0;
   out_5197906072130444471[295] = 0;
   out_5197906072130444471[296] = 0;
   out_5197906072130444471[297] = 0;
   out_5197906072130444471[298] = 0;
   out_5197906072130444471[299] = 0;
   out_5197906072130444471[300] = 0;
   out_5197906072130444471[301] = 0;
   out_5197906072130444471[302] = 0;
   out_5197906072130444471[303] = 0;
   out_5197906072130444471[304] = 1;
   out_5197906072130444471[305] = 0;
   out_5197906072130444471[306] = 0;
   out_5197906072130444471[307] = 0;
   out_5197906072130444471[308] = 0;
   out_5197906072130444471[309] = 0;
   out_5197906072130444471[310] = 0;
   out_5197906072130444471[311] = 0;
   out_5197906072130444471[312] = 0;
   out_5197906072130444471[313] = 0;
   out_5197906072130444471[314] = 0;
   out_5197906072130444471[315] = 0;
   out_5197906072130444471[316] = 0;
   out_5197906072130444471[317] = 0;
   out_5197906072130444471[318] = 0;
   out_5197906072130444471[319] = 0;
   out_5197906072130444471[320] = 0;
   out_5197906072130444471[321] = 0;
   out_5197906072130444471[322] = 0;
   out_5197906072130444471[323] = 1;
}
void h_4(double *state, double *unused, double *out_8442663857645814160) {
   out_8442663857645814160[0] = state[6] + state[9];
   out_8442663857645814160[1] = state[7] + state[10];
   out_8442663857645814160[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1223680011297697877) {
   out_1223680011297697877[0] = 0;
   out_1223680011297697877[1] = 0;
   out_1223680011297697877[2] = 0;
   out_1223680011297697877[3] = 0;
   out_1223680011297697877[4] = 0;
   out_1223680011297697877[5] = 0;
   out_1223680011297697877[6] = 1;
   out_1223680011297697877[7] = 0;
   out_1223680011297697877[8] = 0;
   out_1223680011297697877[9] = 1;
   out_1223680011297697877[10] = 0;
   out_1223680011297697877[11] = 0;
   out_1223680011297697877[12] = 0;
   out_1223680011297697877[13] = 0;
   out_1223680011297697877[14] = 0;
   out_1223680011297697877[15] = 0;
   out_1223680011297697877[16] = 0;
   out_1223680011297697877[17] = 0;
   out_1223680011297697877[18] = 0;
   out_1223680011297697877[19] = 0;
   out_1223680011297697877[20] = 0;
   out_1223680011297697877[21] = 0;
   out_1223680011297697877[22] = 0;
   out_1223680011297697877[23] = 0;
   out_1223680011297697877[24] = 0;
   out_1223680011297697877[25] = 1;
   out_1223680011297697877[26] = 0;
   out_1223680011297697877[27] = 0;
   out_1223680011297697877[28] = 1;
   out_1223680011297697877[29] = 0;
   out_1223680011297697877[30] = 0;
   out_1223680011297697877[31] = 0;
   out_1223680011297697877[32] = 0;
   out_1223680011297697877[33] = 0;
   out_1223680011297697877[34] = 0;
   out_1223680011297697877[35] = 0;
   out_1223680011297697877[36] = 0;
   out_1223680011297697877[37] = 0;
   out_1223680011297697877[38] = 0;
   out_1223680011297697877[39] = 0;
   out_1223680011297697877[40] = 0;
   out_1223680011297697877[41] = 0;
   out_1223680011297697877[42] = 0;
   out_1223680011297697877[43] = 0;
   out_1223680011297697877[44] = 1;
   out_1223680011297697877[45] = 0;
   out_1223680011297697877[46] = 0;
   out_1223680011297697877[47] = 1;
   out_1223680011297697877[48] = 0;
   out_1223680011297697877[49] = 0;
   out_1223680011297697877[50] = 0;
   out_1223680011297697877[51] = 0;
   out_1223680011297697877[52] = 0;
   out_1223680011297697877[53] = 0;
}
void h_10(double *state, double *unused, double *out_3964974043036968705) {
   out_3964974043036968705[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3964974043036968705[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3964974043036968705[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5914479273564375913) {
   out_5914479273564375913[0] = 0;
   out_5914479273564375913[1] = 9.8100000000000005*cos(state[1]);
   out_5914479273564375913[2] = 0;
   out_5914479273564375913[3] = 0;
   out_5914479273564375913[4] = -state[8];
   out_5914479273564375913[5] = state[7];
   out_5914479273564375913[6] = 0;
   out_5914479273564375913[7] = state[5];
   out_5914479273564375913[8] = -state[4];
   out_5914479273564375913[9] = 0;
   out_5914479273564375913[10] = 0;
   out_5914479273564375913[11] = 0;
   out_5914479273564375913[12] = 1;
   out_5914479273564375913[13] = 0;
   out_5914479273564375913[14] = 0;
   out_5914479273564375913[15] = 1;
   out_5914479273564375913[16] = 0;
   out_5914479273564375913[17] = 0;
   out_5914479273564375913[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5914479273564375913[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5914479273564375913[20] = 0;
   out_5914479273564375913[21] = state[8];
   out_5914479273564375913[22] = 0;
   out_5914479273564375913[23] = -state[6];
   out_5914479273564375913[24] = -state[5];
   out_5914479273564375913[25] = 0;
   out_5914479273564375913[26] = state[3];
   out_5914479273564375913[27] = 0;
   out_5914479273564375913[28] = 0;
   out_5914479273564375913[29] = 0;
   out_5914479273564375913[30] = 0;
   out_5914479273564375913[31] = 1;
   out_5914479273564375913[32] = 0;
   out_5914479273564375913[33] = 0;
   out_5914479273564375913[34] = 1;
   out_5914479273564375913[35] = 0;
   out_5914479273564375913[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5914479273564375913[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5914479273564375913[38] = 0;
   out_5914479273564375913[39] = -state[7];
   out_5914479273564375913[40] = state[6];
   out_5914479273564375913[41] = 0;
   out_5914479273564375913[42] = state[4];
   out_5914479273564375913[43] = -state[3];
   out_5914479273564375913[44] = 0;
   out_5914479273564375913[45] = 0;
   out_5914479273564375913[46] = 0;
   out_5914479273564375913[47] = 0;
   out_5914479273564375913[48] = 0;
   out_5914479273564375913[49] = 0;
   out_5914479273564375913[50] = 1;
   out_5914479273564375913[51] = 0;
   out_5914479273564375913[52] = 0;
   out_5914479273564375913[53] = 1;
}
void h_13(double *state, double *unused, double *out_8876471781075959631) {
   out_8876471781075959631[0] = state[3];
   out_8876471781075959631[1] = state[4];
   out_8876471781075959631[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1988593814034634924) {
   out_1988593814034634924[0] = 0;
   out_1988593814034634924[1] = 0;
   out_1988593814034634924[2] = 0;
   out_1988593814034634924[3] = 1;
   out_1988593814034634924[4] = 0;
   out_1988593814034634924[5] = 0;
   out_1988593814034634924[6] = 0;
   out_1988593814034634924[7] = 0;
   out_1988593814034634924[8] = 0;
   out_1988593814034634924[9] = 0;
   out_1988593814034634924[10] = 0;
   out_1988593814034634924[11] = 0;
   out_1988593814034634924[12] = 0;
   out_1988593814034634924[13] = 0;
   out_1988593814034634924[14] = 0;
   out_1988593814034634924[15] = 0;
   out_1988593814034634924[16] = 0;
   out_1988593814034634924[17] = 0;
   out_1988593814034634924[18] = 0;
   out_1988593814034634924[19] = 0;
   out_1988593814034634924[20] = 0;
   out_1988593814034634924[21] = 0;
   out_1988593814034634924[22] = 1;
   out_1988593814034634924[23] = 0;
   out_1988593814034634924[24] = 0;
   out_1988593814034634924[25] = 0;
   out_1988593814034634924[26] = 0;
   out_1988593814034634924[27] = 0;
   out_1988593814034634924[28] = 0;
   out_1988593814034634924[29] = 0;
   out_1988593814034634924[30] = 0;
   out_1988593814034634924[31] = 0;
   out_1988593814034634924[32] = 0;
   out_1988593814034634924[33] = 0;
   out_1988593814034634924[34] = 0;
   out_1988593814034634924[35] = 0;
   out_1988593814034634924[36] = 0;
   out_1988593814034634924[37] = 0;
   out_1988593814034634924[38] = 0;
   out_1988593814034634924[39] = 0;
   out_1988593814034634924[40] = 0;
   out_1988593814034634924[41] = 1;
   out_1988593814034634924[42] = 0;
   out_1988593814034634924[43] = 0;
   out_1988593814034634924[44] = 0;
   out_1988593814034634924[45] = 0;
   out_1988593814034634924[46] = 0;
   out_1988593814034634924[47] = 0;
   out_1988593814034634924[48] = 0;
   out_1988593814034634924[49] = 0;
   out_1988593814034634924[50] = 0;
   out_1988593814034634924[51] = 0;
   out_1988593814034634924[52] = 0;
   out_1988593814034634924[53] = 0;
}
void h_14(double *state, double *unused, double *out_8405881405530134324) {
   out_8405881405530134324[0] = state[6];
   out_8405881405530134324[1] = state[7];
   out_8405881405530134324[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1658796537942581476) {
   out_1658796537942581476[0] = 0;
   out_1658796537942581476[1] = 0;
   out_1658796537942581476[2] = 0;
   out_1658796537942581476[3] = 0;
   out_1658796537942581476[4] = 0;
   out_1658796537942581476[5] = 0;
   out_1658796537942581476[6] = 1;
   out_1658796537942581476[7] = 0;
   out_1658796537942581476[8] = 0;
   out_1658796537942581476[9] = 0;
   out_1658796537942581476[10] = 0;
   out_1658796537942581476[11] = 0;
   out_1658796537942581476[12] = 0;
   out_1658796537942581476[13] = 0;
   out_1658796537942581476[14] = 0;
   out_1658796537942581476[15] = 0;
   out_1658796537942581476[16] = 0;
   out_1658796537942581476[17] = 0;
   out_1658796537942581476[18] = 0;
   out_1658796537942581476[19] = 0;
   out_1658796537942581476[20] = 0;
   out_1658796537942581476[21] = 0;
   out_1658796537942581476[22] = 0;
   out_1658796537942581476[23] = 0;
   out_1658796537942581476[24] = 0;
   out_1658796537942581476[25] = 1;
   out_1658796537942581476[26] = 0;
   out_1658796537942581476[27] = 0;
   out_1658796537942581476[28] = 0;
   out_1658796537942581476[29] = 0;
   out_1658796537942581476[30] = 0;
   out_1658796537942581476[31] = 0;
   out_1658796537942581476[32] = 0;
   out_1658796537942581476[33] = 0;
   out_1658796537942581476[34] = 0;
   out_1658796537942581476[35] = 0;
   out_1658796537942581476[36] = 0;
   out_1658796537942581476[37] = 0;
   out_1658796537942581476[38] = 0;
   out_1658796537942581476[39] = 0;
   out_1658796537942581476[40] = 0;
   out_1658796537942581476[41] = 0;
   out_1658796537942581476[42] = 0;
   out_1658796537942581476[43] = 0;
   out_1658796537942581476[44] = 1;
   out_1658796537942581476[45] = 0;
   out_1658796537942581476[46] = 0;
   out_1658796537942581476[47] = 0;
   out_1658796537942581476[48] = 0;
   out_1658796537942581476[49] = 0;
   out_1658796537942581476[50] = 0;
   out_1658796537942581476[51] = 0;
   out_1658796537942581476[52] = 0;
   out_1658796537942581476[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7083554587370275014) {
  err_fun(nom_x, delta_x, out_7083554587370275014);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6548503546481104197) {
  inv_err_fun(nom_x, true_x, out_6548503546481104197);
}
void pose_H_mod_fun(double *state, double *out_8484867830328864601) {
  H_mod_fun(state, out_8484867830328864601);
}
void pose_f_fun(double *state, double dt, double *out_6058628880177520660) {
  f_fun(state,  dt, out_6058628880177520660);
}
void pose_F_fun(double *state, double dt, double *out_5197906072130444471) {
  F_fun(state,  dt, out_5197906072130444471);
}
void pose_h_4(double *state, double *unused, double *out_8442663857645814160) {
  h_4(state, unused, out_8442663857645814160);
}
void pose_H_4(double *state, double *unused, double *out_1223680011297697877) {
  H_4(state, unused, out_1223680011297697877);
}
void pose_h_10(double *state, double *unused, double *out_3964974043036968705) {
  h_10(state, unused, out_3964974043036968705);
}
void pose_H_10(double *state, double *unused, double *out_5914479273564375913) {
  H_10(state, unused, out_5914479273564375913);
}
void pose_h_13(double *state, double *unused, double *out_8876471781075959631) {
  h_13(state, unused, out_8876471781075959631);
}
void pose_H_13(double *state, double *unused, double *out_1988593814034634924) {
  H_13(state, unused, out_1988593814034634924);
}
void pose_h_14(double *state, double *unused, double *out_8405881405530134324) {
  h_14(state, unused, out_8405881405530134324);
}
void pose_H_14(double *state, double *unused, double *out_1658796537942581476) {
  H_14(state, unused, out_1658796537942581476);
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
