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
void err_fun(double *nom_x, double *delta_x, double *out_5543923555702989986) {
   out_5543923555702989986[0] = delta_x[0] + nom_x[0];
   out_5543923555702989986[1] = delta_x[1] + nom_x[1];
   out_5543923555702989986[2] = delta_x[2] + nom_x[2];
   out_5543923555702989986[3] = delta_x[3] + nom_x[3];
   out_5543923555702989986[4] = delta_x[4] + nom_x[4];
   out_5543923555702989986[5] = delta_x[5] + nom_x[5];
   out_5543923555702989986[6] = delta_x[6] + nom_x[6];
   out_5543923555702989986[7] = delta_x[7] + nom_x[7];
   out_5543923555702989986[8] = delta_x[8] + nom_x[8];
   out_5543923555702989986[9] = delta_x[9] + nom_x[9];
   out_5543923555702989986[10] = delta_x[10] + nom_x[10];
   out_5543923555702989986[11] = delta_x[11] + nom_x[11];
   out_5543923555702989986[12] = delta_x[12] + nom_x[12];
   out_5543923555702989986[13] = delta_x[13] + nom_x[13];
   out_5543923555702989986[14] = delta_x[14] + nom_x[14];
   out_5543923555702989986[15] = delta_x[15] + nom_x[15];
   out_5543923555702989986[16] = delta_x[16] + nom_x[16];
   out_5543923555702989986[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8171878046525728238) {
   out_8171878046525728238[0] = -nom_x[0] + true_x[0];
   out_8171878046525728238[1] = -nom_x[1] + true_x[1];
   out_8171878046525728238[2] = -nom_x[2] + true_x[2];
   out_8171878046525728238[3] = -nom_x[3] + true_x[3];
   out_8171878046525728238[4] = -nom_x[4] + true_x[4];
   out_8171878046525728238[5] = -nom_x[5] + true_x[5];
   out_8171878046525728238[6] = -nom_x[6] + true_x[6];
   out_8171878046525728238[7] = -nom_x[7] + true_x[7];
   out_8171878046525728238[8] = -nom_x[8] + true_x[8];
   out_8171878046525728238[9] = -nom_x[9] + true_x[9];
   out_8171878046525728238[10] = -nom_x[10] + true_x[10];
   out_8171878046525728238[11] = -nom_x[11] + true_x[11];
   out_8171878046525728238[12] = -nom_x[12] + true_x[12];
   out_8171878046525728238[13] = -nom_x[13] + true_x[13];
   out_8171878046525728238[14] = -nom_x[14] + true_x[14];
   out_8171878046525728238[15] = -nom_x[15] + true_x[15];
   out_8171878046525728238[16] = -nom_x[16] + true_x[16];
   out_8171878046525728238[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5690553283304626846) {
   out_5690553283304626846[0] = 1.0;
   out_5690553283304626846[1] = 0.0;
   out_5690553283304626846[2] = 0.0;
   out_5690553283304626846[3] = 0.0;
   out_5690553283304626846[4] = 0.0;
   out_5690553283304626846[5] = 0.0;
   out_5690553283304626846[6] = 0.0;
   out_5690553283304626846[7] = 0.0;
   out_5690553283304626846[8] = 0.0;
   out_5690553283304626846[9] = 0.0;
   out_5690553283304626846[10] = 0.0;
   out_5690553283304626846[11] = 0.0;
   out_5690553283304626846[12] = 0.0;
   out_5690553283304626846[13] = 0.0;
   out_5690553283304626846[14] = 0.0;
   out_5690553283304626846[15] = 0.0;
   out_5690553283304626846[16] = 0.0;
   out_5690553283304626846[17] = 0.0;
   out_5690553283304626846[18] = 0.0;
   out_5690553283304626846[19] = 1.0;
   out_5690553283304626846[20] = 0.0;
   out_5690553283304626846[21] = 0.0;
   out_5690553283304626846[22] = 0.0;
   out_5690553283304626846[23] = 0.0;
   out_5690553283304626846[24] = 0.0;
   out_5690553283304626846[25] = 0.0;
   out_5690553283304626846[26] = 0.0;
   out_5690553283304626846[27] = 0.0;
   out_5690553283304626846[28] = 0.0;
   out_5690553283304626846[29] = 0.0;
   out_5690553283304626846[30] = 0.0;
   out_5690553283304626846[31] = 0.0;
   out_5690553283304626846[32] = 0.0;
   out_5690553283304626846[33] = 0.0;
   out_5690553283304626846[34] = 0.0;
   out_5690553283304626846[35] = 0.0;
   out_5690553283304626846[36] = 0.0;
   out_5690553283304626846[37] = 0.0;
   out_5690553283304626846[38] = 1.0;
   out_5690553283304626846[39] = 0.0;
   out_5690553283304626846[40] = 0.0;
   out_5690553283304626846[41] = 0.0;
   out_5690553283304626846[42] = 0.0;
   out_5690553283304626846[43] = 0.0;
   out_5690553283304626846[44] = 0.0;
   out_5690553283304626846[45] = 0.0;
   out_5690553283304626846[46] = 0.0;
   out_5690553283304626846[47] = 0.0;
   out_5690553283304626846[48] = 0.0;
   out_5690553283304626846[49] = 0.0;
   out_5690553283304626846[50] = 0.0;
   out_5690553283304626846[51] = 0.0;
   out_5690553283304626846[52] = 0.0;
   out_5690553283304626846[53] = 0.0;
   out_5690553283304626846[54] = 0.0;
   out_5690553283304626846[55] = 0.0;
   out_5690553283304626846[56] = 0.0;
   out_5690553283304626846[57] = 1.0;
   out_5690553283304626846[58] = 0.0;
   out_5690553283304626846[59] = 0.0;
   out_5690553283304626846[60] = 0.0;
   out_5690553283304626846[61] = 0.0;
   out_5690553283304626846[62] = 0.0;
   out_5690553283304626846[63] = 0.0;
   out_5690553283304626846[64] = 0.0;
   out_5690553283304626846[65] = 0.0;
   out_5690553283304626846[66] = 0.0;
   out_5690553283304626846[67] = 0.0;
   out_5690553283304626846[68] = 0.0;
   out_5690553283304626846[69] = 0.0;
   out_5690553283304626846[70] = 0.0;
   out_5690553283304626846[71] = 0.0;
   out_5690553283304626846[72] = 0.0;
   out_5690553283304626846[73] = 0.0;
   out_5690553283304626846[74] = 0.0;
   out_5690553283304626846[75] = 0.0;
   out_5690553283304626846[76] = 1.0;
   out_5690553283304626846[77] = 0.0;
   out_5690553283304626846[78] = 0.0;
   out_5690553283304626846[79] = 0.0;
   out_5690553283304626846[80] = 0.0;
   out_5690553283304626846[81] = 0.0;
   out_5690553283304626846[82] = 0.0;
   out_5690553283304626846[83] = 0.0;
   out_5690553283304626846[84] = 0.0;
   out_5690553283304626846[85] = 0.0;
   out_5690553283304626846[86] = 0.0;
   out_5690553283304626846[87] = 0.0;
   out_5690553283304626846[88] = 0.0;
   out_5690553283304626846[89] = 0.0;
   out_5690553283304626846[90] = 0.0;
   out_5690553283304626846[91] = 0.0;
   out_5690553283304626846[92] = 0.0;
   out_5690553283304626846[93] = 0.0;
   out_5690553283304626846[94] = 0.0;
   out_5690553283304626846[95] = 1.0;
   out_5690553283304626846[96] = 0.0;
   out_5690553283304626846[97] = 0.0;
   out_5690553283304626846[98] = 0.0;
   out_5690553283304626846[99] = 0.0;
   out_5690553283304626846[100] = 0.0;
   out_5690553283304626846[101] = 0.0;
   out_5690553283304626846[102] = 0.0;
   out_5690553283304626846[103] = 0.0;
   out_5690553283304626846[104] = 0.0;
   out_5690553283304626846[105] = 0.0;
   out_5690553283304626846[106] = 0.0;
   out_5690553283304626846[107] = 0.0;
   out_5690553283304626846[108] = 0.0;
   out_5690553283304626846[109] = 0.0;
   out_5690553283304626846[110] = 0.0;
   out_5690553283304626846[111] = 0.0;
   out_5690553283304626846[112] = 0.0;
   out_5690553283304626846[113] = 0.0;
   out_5690553283304626846[114] = 1.0;
   out_5690553283304626846[115] = 0.0;
   out_5690553283304626846[116] = 0.0;
   out_5690553283304626846[117] = 0.0;
   out_5690553283304626846[118] = 0.0;
   out_5690553283304626846[119] = 0.0;
   out_5690553283304626846[120] = 0.0;
   out_5690553283304626846[121] = 0.0;
   out_5690553283304626846[122] = 0.0;
   out_5690553283304626846[123] = 0.0;
   out_5690553283304626846[124] = 0.0;
   out_5690553283304626846[125] = 0.0;
   out_5690553283304626846[126] = 0.0;
   out_5690553283304626846[127] = 0.0;
   out_5690553283304626846[128] = 0.0;
   out_5690553283304626846[129] = 0.0;
   out_5690553283304626846[130] = 0.0;
   out_5690553283304626846[131] = 0.0;
   out_5690553283304626846[132] = 0.0;
   out_5690553283304626846[133] = 1.0;
   out_5690553283304626846[134] = 0.0;
   out_5690553283304626846[135] = 0.0;
   out_5690553283304626846[136] = 0.0;
   out_5690553283304626846[137] = 0.0;
   out_5690553283304626846[138] = 0.0;
   out_5690553283304626846[139] = 0.0;
   out_5690553283304626846[140] = 0.0;
   out_5690553283304626846[141] = 0.0;
   out_5690553283304626846[142] = 0.0;
   out_5690553283304626846[143] = 0.0;
   out_5690553283304626846[144] = 0.0;
   out_5690553283304626846[145] = 0.0;
   out_5690553283304626846[146] = 0.0;
   out_5690553283304626846[147] = 0.0;
   out_5690553283304626846[148] = 0.0;
   out_5690553283304626846[149] = 0.0;
   out_5690553283304626846[150] = 0.0;
   out_5690553283304626846[151] = 0.0;
   out_5690553283304626846[152] = 1.0;
   out_5690553283304626846[153] = 0.0;
   out_5690553283304626846[154] = 0.0;
   out_5690553283304626846[155] = 0.0;
   out_5690553283304626846[156] = 0.0;
   out_5690553283304626846[157] = 0.0;
   out_5690553283304626846[158] = 0.0;
   out_5690553283304626846[159] = 0.0;
   out_5690553283304626846[160] = 0.0;
   out_5690553283304626846[161] = 0.0;
   out_5690553283304626846[162] = 0.0;
   out_5690553283304626846[163] = 0.0;
   out_5690553283304626846[164] = 0.0;
   out_5690553283304626846[165] = 0.0;
   out_5690553283304626846[166] = 0.0;
   out_5690553283304626846[167] = 0.0;
   out_5690553283304626846[168] = 0.0;
   out_5690553283304626846[169] = 0.0;
   out_5690553283304626846[170] = 0.0;
   out_5690553283304626846[171] = 1.0;
   out_5690553283304626846[172] = 0.0;
   out_5690553283304626846[173] = 0.0;
   out_5690553283304626846[174] = 0.0;
   out_5690553283304626846[175] = 0.0;
   out_5690553283304626846[176] = 0.0;
   out_5690553283304626846[177] = 0.0;
   out_5690553283304626846[178] = 0.0;
   out_5690553283304626846[179] = 0.0;
   out_5690553283304626846[180] = 0.0;
   out_5690553283304626846[181] = 0.0;
   out_5690553283304626846[182] = 0.0;
   out_5690553283304626846[183] = 0.0;
   out_5690553283304626846[184] = 0.0;
   out_5690553283304626846[185] = 0.0;
   out_5690553283304626846[186] = 0.0;
   out_5690553283304626846[187] = 0.0;
   out_5690553283304626846[188] = 0.0;
   out_5690553283304626846[189] = 0.0;
   out_5690553283304626846[190] = 1.0;
   out_5690553283304626846[191] = 0.0;
   out_5690553283304626846[192] = 0.0;
   out_5690553283304626846[193] = 0.0;
   out_5690553283304626846[194] = 0.0;
   out_5690553283304626846[195] = 0.0;
   out_5690553283304626846[196] = 0.0;
   out_5690553283304626846[197] = 0.0;
   out_5690553283304626846[198] = 0.0;
   out_5690553283304626846[199] = 0.0;
   out_5690553283304626846[200] = 0.0;
   out_5690553283304626846[201] = 0.0;
   out_5690553283304626846[202] = 0.0;
   out_5690553283304626846[203] = 0.0;
   out_5690553283304626846[204] = 0.0;
   out_5690553283304626846[205] = 0.0;
   out_5690553283304626846[206] = 0.0;
   out_5690553283304626846[207] = 0.0;
   out_5690553283304626846[208] = 0.0;
   out_5690553283304626846[209] = 1.0;
   out_5690553283304626846[210] = 0.0;
   out_5690553283304626846[211] = 0.0;
   out_5690553283304626846[212] = 0.0;
   out_5690553283304626846[213] = 0.0;
   out_5690553283304626846[214] = 0.0;
   out_5690553283304626846[215] = 0.0;
   out_5690553283304626846[216] = 0.0;
   out_5690553283304626846[217] = 0.0;
   out_5690553283304626846[218] = 0.0;
   out_5690553283304626846[219] = 0.0;
   out_5690553283304626846[220] = 0.0;
   out_5690553283304626846[221] = 0.0;
   out_5690553283304626846[222] = 0.0;
   out_5690553283304626846[223] = 0.0;
   out_5690553283304626846[224] = 0.0;
   out_5690553283304626846[225] = 0.0;
   out_5690553283304626846[226] = 0.0;
   out_5690553283304626846[227] = 0.0;
   out_5690553283304626846[228] = 1.0;
   out_5690553283304626846[229] = 0.0;
   out_5690553283304626846[230] = 0.0;
   out_5690553283304626846[231] = 0.0;
   out_5690553283304626846[232] = 0.0;
   out_5690553283304626846[233] = 0.0;
   out_5690553283304626846[234] = 0.0;
   out_5690553283304626846[235] = 0.0;
   out_5690553283304626846[236] = 0.0;
   out_5690553283304626846[237] = 0.0;
   out_5690553283304626846[238] = 0.0;
   out_5690553283304626846[239] = 0.0;
   out_5690553283304626846[240] = 0.0;
   out_5690553283304626846[241] = 0.0;
   out_5690553283304626846[242] = 0.0;
   out_5690553283304626846[243] = 0.0;
   out_5690553283304626846[244] = 0.0;
   out_5690553283304626846[245] = 0.0;
   out_5690553283304626846[246] = 0.0;
   out_5690553283304626846[247] = 1.0;
   out_5690553283304626846[248] = 0.0;
   out_5690553283304626846[249] = 0.0;
   out_5690553283304626846[250] = 0.0;
   out_5690553283304626846[251] = 0.0;
   out_5690553283304626846[252] = 0.0;
   out_5690553283304626846[253] = 0.0;
   out_5690553283304626846[254] = 0.0;
   out_5690553283304626846[255] = 0.0;
   out_5690553283304626846[256] = 0.0;
   out_5690553283304626846[257] = 0.0;
   out_5690553283304626846[258] = 0.0;
   out_5690553283304626846[259] = 0.0;
   out_5690553283304626846[260] = 0.0;
   out_5690553283304626846[261] = 0.0;
   out_5690553283304626846[262] = 0.0;
   out_5690553283304626846[263] = 0.0;
   out_5690553283304626846[264] = 0.0;
   out_5690553283304626846[265] = 0.0;
   out_5690553283304626846[266] = 1.0;
   out_5690553283304626846[267] = 0.0;
   out_5690553283304626846[268] = 0.0;
   out_5690553283304626846[269] = 0.0;
   out_5690553283304626846[270] = 0.0;
   out_5690553283304626846[271] = 0.0;
   out_5690553283304626846[272] = 0.0;
   out_5690553283304626846[273] = 0.0;
   out_5690553283304626846[274] = 0.0;
   out_5690553283304626846[275] = 0.0;
   out_5690553283304626846[276] = 0.0;
   out_5690553283304626846[277] = 0.0;
   out_5690553283304626846[278] = 0.0;
   out_5690553283304626846[279] = 0.0;
   out_5690553283304626846[280] = 0.0;
   out_5690553283304626846[281] = 0.0;
   out_5690553283304626846[282] = 0.0;
   out_5690553283304626846[283] = 0.0;
   out_5690553283304626846[284] = 0.0;
   out_5690553283304626846[285] = 1.0;
   out_5690553283304626846[286] = 0.0;
   out_5690553283304626846[287] = 0.0;
   out_5690553283304626846[288] = 0.0;
   out_5690553283304626846[289] = 0.0;
   out_5690553283304626846[290] = 0.0;
   out_5690553283304626846[291] = 0.0;
   out_5690553283304626846[292] = 0.0;
   out_5690553283304626846[293] = 0.0;
   out_5690553283304626846[294] = 0.0;
   out_5690553283304626846[295] = 0.0;
   out_5690553283304626846[296] = 0.0;
   out_5690553283304626846[297] = 0.0;
   out_5690553283304626846[298] = 0.0;
   out_5690553283304626846[299] = 0.0;
   out_5690553283304626846[300] = 0.0;
   out_5690553283304626846[301] = 0.0;
   out_5690553283304626846[302] = 0.0;
   out_5690553283304626846[303] = 0.0;
   out_5690553283304626846[304] = 1.0;
   out_5690553283304626846[305] = 0.0;
   out_5690553283304626846[306] = 0.0;
   out_5690553283304626846[307] = 0.0;
   out_5690553283304626846[308] = 0.0;
   out_5690553283304626846[309] = 0.0;
   out_5690553283304626846[310] = 0.0;
   out_5690553283304626846[311] = 0.0;
   out_5690553283304626846[312] = 0.0;
   out_5690553283304626846[313] = 0.0;
   out_5690553283304626846[314] = 0.0;
   out_5690553283304626846[315] = 0.0;
   out_5690553283304626846[316] = 0.0;
   out_5690553283304626846[317] = 0.0;
   out_5690553283304626846[318] = 0.0;
   out_5690553283304626846[319] = 0.0;
   out_5690553283304626846[320] = 0.0;
   out_5690553283304626846[321] = 0.0;
   out_5690553283304626846[322] = 0.0;
   out_5690553283304626846[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5317158281057841296) {
   out_5317158281057841296[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5317158281057841296[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5317158281057841296[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5317158281057841296[3] = dt*state[12] + state[3];
   out_5317158281057841296[4] = dt*state[13] + state[4];
   out_5317158281057841296[5] = dt*state[14] + state[5];
   out_5317158281057841296[6] = state[6];
   out_5317158281057841296[7] = state[7];
   out_5317158281057841296[8] = state[8];
   out_5317158281057841296[9] = state[9];
   out_5317158281057841296[10] = state[10];
   out_5317158281057841296[11] = state[11];
   out_5317158281057841296[12] = state[12];
   out_5317158281057841296[13] = state[13];
   out_5317158281057841296[14] = state[14];
   out_5317158281057841296[15] = state[15];
   out_5317158281057841296[16] = state[16];
   out_5317158281057841296[17] = state[17];
}
void F_fun(double *state, double dt, double *out_34764116407898728) {
   out_34764116407898728[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_34764116407898728[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_34764116407898728[2] = 0;
   out_34764116407898728[3] = 0;
   out_34764116407898728[4] = 0;
   out_34764116407898728[5] = 0;
   out_34764116407898728[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_34764116407898728[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_34764116407898728[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_34764116407898728[9] = 0;
   out_34764116407898728[10] = 0;
   out_34764116407898728[11] = 0;
   out_34764116407898728[12] = 0;
   out_34764116407898728[13] = 0;
   out_34764116407898728[14] = 0;
   out_34764116407898728[15] = 0;
   out_34764116407898728[16] = 0;
   out_34764116407898728[17] = 0;
   out_34764116407898728[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_34764116407898728[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_34764116407898728[20] = 0;
   out_34764116407898728[21] = 0;
   out_34764116407898728[22] = 0;
   out_34764116407898728[23] = 0;
   out_34764116407898728[24] = 0;
   out_34764116407898728[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_34764116407898728[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_34764116407898728[27] = 0;
   out_34764116407898728[28] = 0;
   out_34764116407898728[29] = 0;
   out_34764116407898728[30] = 0;
   out_34764116407898728[31] = 0;
   out_34764116407898728[32] = 0;
   out_34764116407898728[33] = 0;
   out_34764116407898728[34] = 0;
   out_34764116407898728[35] = 0;
   out_34764116407898728[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_34764116407898728[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_34764116407898728[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_34764116407898728[39] = 0;
   out_34764116407898728[40] = 0;
   out_34764116407898728[41] = 0;
   out_34764116407898728[42] = 0;
   out_34764116407898728[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_34764116407898728[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_34764116407898728[45] = 0;
   out_34764116407898728[46] = 0;
   out_34764116407898728[47] = 0;
   out_34764116407898728[48] = 0;
   out_34764116407898728[49] = 0;
   out_34764116407898728[50] = 0;
   out_34764116407898728[51] = 0;
   out_34764116407898728[52] = 0;
   out_34764116407898728[53] = 0;
   out_34764116407898728[54] = 0;
   out_34764116407898728[55] = 0;
   out_34764116407898728[56] = 0;
   out_34764116407898728[57] = 1;
   out_34764116407898728[58] = 0;
   out_34764116407898728[59] = 0;
   out_34764116407898728[60] = 0;
   out_34764116407898728[61] = 0;
   out_34764116407898728[62] = 0;
   out_34764116407898728[63] = 0;
   out_34764116407898728[64] = 0;
   out_34764116407898728[65] = 0;
   out_34764116407898728[66] = dt;
   out_34764116407898728[67] = 0;
   out_34764116407898728[68] = 0;
   out_34764116407898728[69] = 0;
   out_34764116407898728[70] = 0;
   out_34764116407898728[71] = 0;
   out_34764116407898728[72] = 0;
   out_34764116407898728[73] = 0;
   out_34764116407898728[74] = 0;
   out_34764116407898728[75] = 0;
   out_34764116407898728[76] = 1;
   out_34764116407898728[77] = 0;
   out_34764116407898728[78] = 0;
   out_34764116407898728[79] = 0;
   out_34764116407898728[80] = 0;
   out_34764116407898728[81] = 0;
   out_34764116407898728[82] = 0;
   out_34764116407898728[83] = 0;
   out_34764116407898728[84] = 0;
   out_34764116407898728[85] = dt;
   out_34764116407898728[86] = 0;
   out_34764116407898728[87] = 0;
   out_34764116407898728[88] = 0;
   out_34764116407898728[89] = 0;
   out_34764116407898728[90] = 0;
   out_34764116407898728[91] = 0;
   out_34764116407898728[92] = 0;
   out_34764116407898728[93] = 0;
   out_34764116407898728[94] = 0;
   out_34764116407898728[95] = 1;
   out_34764116407898728[96] = 0;
   out_34764116407898728[97] = 0;
   out_34764116407898728[98] = 0;
   out_34764116407898728[99] = 0;
   out_34764116407898728[100] = 0;
   out_34764116407898728[101] = 0;
   out_34764116407898728[102] = 0;
   out_34764116407898728[103] = 0;
   out_34764116407898728[104] = dt;
   out_34764116407898728[105] = 0;
   out_34764116407898728[106] = 0;
   out_34764116407898728[107] = 0;
   out_34764116407898728[108] = 0;
   out_34764116407898728[109] = 0;
   out_34764116407898728[110] = 0;
   out_34764116407898728[111] = 0;
   out_34764116407898728[112] = 0;
   out_34764116407898728[113] = 0;
   out_34764116407898728[114] = 1;
   out_34764116407898728[115] = 0;
   out_34764116407898728[116] = 0;
   out_34764116407898728[117] = 0;
   out_34764116407898728[118] = 0;
   out_34764116407898728[119] = 0;
   out_34764116407898728[120] = 0;
   out_34764116407898728[121] = 0;
   out_34764116407898728[122] = 0;
   out_34764116407898728[123] = 0;
   out_34764116407898728[124] = 0;
   out_34764116407898728[125] = 0;
   out_34764116407898728[126] = 0;
   out_34764116407898728[127] = 0;
   out_34764116407898728[128] = 0;
   out_34764116407898728[129] = 0;
   out_34764116407898728[130] = 0;
   out_34764116407898728[131] = 0;
   out_34764116407898728[132] = 0;
   out_34764116407898728[133] = 1;
   out_34764116407898728[134] = 0;
   out_34764116407898728[135] = 0;
   out_34764116407898728[136] = 0;
   out_34764116407898728[137] = 0;
   out_34764116407898728[138] = 0;
   out_34764116407898728[139] = 0;
   out_34764116407898728[140] = 0;
   out_34764116407898728[141] = 0;
   out_34764116407898728[142] = 0;
   out_34764116407898728[143] = 0;
   out_34764116407898728[144] = 0;
   out_34764116407898728[145] = 0;
   out_34764116407898728[146] = 0;
   out_34764116407898728[147] = 0;
   out_34764116407898728[148] = 0;
   out_34764116407898728[149] = 0;
   out_34764116407898728[150] = 0;
   out_34764116407898728[151] = 0;
   out_34764116407898728[152] = 1;
   out_34764116407898728[153] = 0;
   out_34764116407898728[154] = 0;
   out_34764116407898728[155] = 0;
   out_34764116407898728[156] = 0;
   out_34764116407898728[157] = 0;
   out_34764116407898728[158] = 0;
   out_34764116407898728[159] = 0;
   out_34764116407898728[160] = 0;
   out_34764116407898728[161] = 0;
   out_34764116407898728[162] = 0;
   out_34764116407898728[163] = 0;
   out_34764116407898728[164] = 0;
   out_34764116407898728[165] = 0;
   out_34764116407898728[166] = 0;
   out_34764116407898728[167] = 0;
   out_34764116407898728[168] = 0;
   out_34764116407898728[169] = 0;
   out_34764116407898728[170] = 0;
   out_34764116407898728[171] = 1;
   out_34764116407898728[172] = 0;
   out_34764116407898728[173] = 0;
   out_34764116407898728[174] = 0;
   out_34764116407898728[175] = 0;
   out_34764116407898728[176] = 0;
   out_34764116407898728[177] = 0;
   out_34764116407898728[178] = 0;
   out_34764116407898728[179] = 0;
   out_34764116407898728[180] = 0;
   out_34764116407898728[181] = 0;
   out_34764116407898728[182] = 0;
   out_34764116407898728[183] = 0;
   out_34764116407898728[184] = 0;
   out_34764116407898728[185] = 0;
   out_34764116407898728[186] = 0;
   out_34764116407898728[187] = 0;
   out_34764116407898728[188] = 0;
   out_34764116407898728[189] = 0;
   out_34764116407898728[190] = 1;
   out_34764116407898728[191] = 0;
   out_34764116407898728[192] = 0;
   out_34764116407898728[193] = 0;
   out_34764116407898728[194] = 0;
   out_34764116407898728[195] = 0;
   out_34764116407898728[196] = 0;
   out_34764116407898728[197] = 0;
   out_34764116407898728[198] = 0;
   out_34764116407898728[199] = 0;
   out_34764116407898728[200] = 0;
   out_34764116407898728[201] = 0;
   out_34764116407898728[202] = 0;
   out_34764116407898728[203] = 0;
   out_34764116407898728[204] = 0;
   out_34764116407898728[205] = 0;
   out_34764116407898728[206] = 0;
   out_34764116407898728[207] = 0;
   out_34764116407898728[208] = 0;
   out_34764116407898728[209] = 1;
   out_34764116407898728[210] = 0;
   out_34764116407898728[211] = 0;
   out_34764116407898728[212] = 0;
   out_34764116407898728[213] = 0;
   out_34764116407898728[214] = 0;
   out_34764116407898728[215] = 0;
   out_34764116407898728[216] = 0;
   out_34764116407898728[217] = 0;
   out_34764116407898728[218] = 0;
   out_34764116407898728[219] = 0;
   out_34764116407898728[220] = 0;
   out_34764116407898728[221] = 0;
   out_34764116407898728[222] = 0;
   out_34764116407898728[223] = 0;
   out_34764116407898728[224] = 0;
   out_34764116407898728[225] = 0;
   out_34764116407898728[226] = 0;
   out_34764116407898728[227] = 0;
   out_34764116407898728[228] = 1;
   out_34764116407898728[229] = 0;
   out_34764116407898728[230] = 0;
   out_34764116407898728[231] = 0;
   out_34764116407898728[232] = 0;
   out_34764116407898728[233] = 0;
   out_34764116407898728[234] = 0;
   out_34764116407898728[235] = 0;
   out_34764116407898728[236] = 0;
   out_34764116407898728[237] = 0;
   out_34764116407898728[238] = 0;
   out_34764116407898728[239] = 0;
   out_34764116407898728[240] = 0;
   out_34764116407898728[241] = 0;
   out_34764116407898728[242] = 0;
   out_34764116407898728[243] = 0;
   out_34764116407898728[244] = 0;
   out_34764116407898728[245] = 0;
   out_34764116407898728[246] = 0;
   out_34764116407898728[247] = 1;
   out_34764116407898728[248] = 0;
   out_34764116407898728[249] = 0;
   out_34764116407898728[250] = 0;
   out_34764116407898728[251] = 0;
   out_34764116407898728[252] = 0;
   out_34764116407898728[253] = 0;
   out_34764116407898728[254] = 0;
   out_34764116407898728[255] = 0;
   out_34764116407898728[256] = 0;
   out_34764116407898728[257] = 0;
   out_34764116407898728[258] = 0;
   out_34764116407898728[259] = 0;
   out_34764116407898728[260] = 0;
   out_34764116407898728[261] = 0;
   out_34764116407898728[262] = 0;
   out_34764116407898728[263] = 0;
   out_34764116407898728[264] = 0;
   out_34764116407898728[265] = 0;
   out_34764116407898728[266] = 1;
   out_34764116407898728[267] = 0;
   out_34764116407898728[268] = 0;
   out_34764116407898728[269] = 0;
   out_34764116407898728[270] = 0;
   out_34764116407898728[271] = 0;
   out_34764116407898728[272] = 0;
   out_34764116407898728[273] = 0;
   out_34764116407898728[274] = 0;
   out_34764116407898728[275] = 0;
   out_34764116407898728[276] = 0;
   out_34764116407898728[277] = 0;
   out_34764116407898728[278] = 0;
   out_34764116407898728[279] = 0;
   out_34764116407898728[280] = 0;
   out_34764116407898728[281] = 0;
   out_34764116407898728[282] = 0;
   out_34764116407898728[283] = 0;
   out_34764116407898728[284] = 0;
   out_34764116407898728[285] = 1;
   out_34764116407898728[286] = 0;
   out_34764116407898728[287] = 0;
   out_34764116407898728[288] = 0;
   out_34764116407898728[289] = 0;
   out_34764116407898728[290] = 0;
   out_34764116407898728[291] = 0;
   out_34764116407898728[292] = 0;
   out_34764116407898728[293] = 0;
   out_34764116407898728[294] = 0;
   out_34764116407898728[295] = 0;
   out_34764116407898728[296] = 0;
   out_34764116407898728[297] = 0;
   out_34764116407898728[298] = 0;
   out_34764116407898728[299] = 0;
   out_34764116407898728[300] = 0;
   out_34764116407898728[301] = 0;
   out_34764116407898728[302] = 0;
   out_34764116407898728[303] = 0;
   out_34764116407898728[304] = 1;
   out_34764116407898728[305] = 0;
   out_34764116407898728[306] = 0;
   out_34764116407898728[307] = 0;
   out_34764116407898728[308] = 0;
   out_34764116407898728[309] = 0;
   out_34764116407898728[310] = 0;
   out_34764116407898728[311] = 0;
   out_34764116407898728[312] = 0;
   out_34764116407898728[313] = 0;
   out_34764116407898728[314] = 0;
   out_34764116407898728[315] = 0;
   out_34764116407898728[316] = 0;
   out_34764116407898728[317] = 0;
   out_34764116407898728[318] = 0;
   out_34764116407898728[319] = 0;
   out_34764116407898728[320] = 0;
   out_34764116407898728[321] = 0;
   out_34764116407898728[322] = 0;
   out_34764116407898728[323] = 1;
}
void h_4(double *state, double *unused, double *out_2611058549638811197) {
   out_2611058549638811197[0] = state[6] + state[9];
   out_2611058549638811197[1] = state[7] + state[10];
   out_2611058549638811197[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3253808382753194496) {
   out_3253808382753194496[0] = 0;
   out_3253808382753194496[1] = 0;
   out_3253808382753194496[2] = 0;
   out_3253808382753194496[3] = 0;
   out_3253808382753194496[4] = 0;
   out_3253808382753194496[5] = 0;
   out_3253808382753194496[6] = 1;
   out_3253808382753194496[7] = 0;
   out_3253808382753194496[8] = 0;
   out_3253808382753194496[9] = 1;
   out_3253808382753194496[10] = 0;
   out_3253808382753194496[11] = 0;
   out_3253808382753194496[12] = 0;
   out_3253808382753194496[13] = 0;
   out_3253808382753194496[14] = 0;
   out_3253808382753194496[15] = 0;
   out_3253808382753194496[16] = 0;
   out_3253808382753194496[17] = 0;
   out_3253808382753194496[18] = 0;
   out_3253808382753194496[19] = 0;
   out_3253808382753194496[20] = 0;
   out_3253808382753194496[21] = 0;
   out_3253808382753194496[22] = 0;
   out_3253808382753194496[23] = 0;
   out_3253808382753194496[24] = 0;
   out_3253808382753194496[25] = 1;
   out_3253808382753194496[26] = 0;
   out_3253808382753194496[27] = 0;
   out_3253808382753194496[28] = 1;
   out_3253808382753194496[29] = 0;
   out_3253808382753194496[30] = 0;
   out_3253808382753194496[31] = 0;
   out_3253808382753194496[32] = 0;
   out_3253808382753194496[33] = 0;
   out_3253808382753194496[34] = 0;
   out_3253808382753194496[35] = 0;
   out_3253808382753194496[36] = 0;
   out_3253808382753194496[37] = 0;
   out_3253808382753194496[38] = 0;
   out_3253808382753194496[39] = 0;
   out_3253808382753194496[40] = 0;
   out_3253808382753194496[41] = 0;
   out_3253808382753194496[42] = 0;
   out_3253808382753194496[43] = 0;
   out_3253808382753194496[44] = 1;
   out_3253808382753194496[45] = 0;
   out_3253808382753194496[46] = 0;
   out_3253808382753194496[47] = 1;
   out_3253808382753194496[48] = 0;
   out_3253808382753194496[49] = 0;
   out_3253808382753194496[50] = 0;
   out_3253808382753194496[51] = 0;
   out_3253808382753194496[52] = 0;
   out_3253808382753194496[53] = 0;
}
void h_10(double *state, double *unused, double *out_8670807093231338393) {
   out_8670807093231338393[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_8670807093231338393[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_8670807093231338393[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_718769444777682190) {
   out_718769444777682190[0] = 0;
   out_718769444777682190[1] = 9.8100000000000005*cos(state[1]);
   out_718769444777682190[2] = 0;
   out_718769444777682190[3] = 0;
   out_718769444777682190[4] = -state[8];
   out_718769444777682190[5] = state[7];
   out_718769444777682190[6] = 0;
   out_718769444777682190[7] = state[5];
   out_718769444777682190[8] = -state[4];
   out_718769444777682190[9] = 0;
   out_718769444777682190[10] = 0;
   out_718769444777682190[11] = 0;
   out_718769444777682190[12] = 1;
   out_718769444777682190[13] = 0;
   out_718769444777682190[14] = 0;
   out_718769444777682190[15] = 1;
   out_718769444777682190[16] = 0;
   out_718769444777682190[17] = 0;
   out_718769444777682190[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_718769444777682190[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_718769444777682190[20] = 0;
   out_718769444777682190[21] = state[8];
   out_718769444777682190[22] = 0;
   out_718769444777682190[23] = -state[6];
   out_718769444777682190[24] = -state[5];
   out_718769444777682190[25] = 0;
   out_718769444777682190[26] = state[3];
   out_718769444777682190[27] = 0;
   out_718769444777682190[28] = 0;
   out_718769444777682190[29] = 0;
   out_718769444777682190[30] = 0;
   out_718769444777682190[31] = 1;
   out_718769444777682190[32] = 0;
   out_718769444777682190[33] = 0;
   out_718769444777682190[34] = 1;
   out_718769444777682190[35] = 0;
   out_718769444777682190[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_718769444777682190[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_718769444777682190[38] = 0;
   out_718769444777682190[39] = -state[7];
   out_718769444777682190[40] = state[6];
   out_718769444777682190[41] = 0;
   out_718769444777682190[42] = state[4];
   out_718769444777682190[43] = -state[3];
   out_718769444777682190[44] = 0;
   out_718769444777682190[45] = 0;
   out_718769444777682190[46] = 0;
   out_718769444777682190[47] = 0;
   out_718769444777682190[48] = 0;
   out_718769444777682190[49] = 0;
   out_718769444777682190[50] = 1;
   out_718769444777682190[51] = 0;
   out_718769444777682190[52] = 0;
   out_718769444777682190[53] = 1;
}
void h_13(double *state, double *unused, double *out_4814072555028059760) {
   out_4814072555028059760[0] = state[3];
   out_4814072555028059760[1] = state[4];
   out_4814072555028059760[2] = state[5];
}
void H_13(double *state, double *unused, double *out_41534557420861695) {
   out_41534557420861695[0] = 0;
   out_41534557420861695[1] = 0;
   out_41534557420861695[2] = 0;
   out_41534557420861695[3] = 1;
   out_41534557420861695[4] = 0;
   out_41534557420861695[5] = 0;
   out_41534557420861695[6] = 0;
   out_41534557420861695[7] = 0;
   out_41534557420861695[8] = 0;
   out_41534557420861695[9] = 0;
   out_41534557420861695[10] = 0;
   out_41534557420861695[11] = 0;
   out_41534557420861695[12] = 0;
   out_41534557420861695[13] = 0;
   out_41534557420861695[14] = 0;
   out_41534557420861695[15] = 0;
   out_41534557420861695[16] = 0;
   out_41534557420861695[17] = 0;
   out_41534557420861695[18] = 0;
   out_41534557420861695[19] = 0;
   out_41534557420861695[20] = 0;
   out_41534557420861695[21] = 0;
   out_41534557420861695[22] = 1;
   out_41534557420861695[23] = 0;
   out_41534557420861695[24] = 0;
   out_41534557420861695[25] = 0;
   out_41534557420861695[26] = 0;
   out_41534557420861695[27] = 0;
   out_41534557420861695[28] = 0;
   out_41534557420861695[29] = 0;
   out_41534557420861695[30] = 0;
   out_41534557420861695[31] = 0;
   out_41534557420861695[32] = 0;
   out_41534557420861695[33] = 0;
   out_41534557420861695[34] = 0;
   out_41534557420861695[35] = 0;
   out_41534557420861695[36] = 0;
   out_41534557420861695[37] = 0;
   out_41534557420861695[38] = 0;
   out_41534557420861695[39] = 0;
   out_41534557420861695[40] = 0;
   out_41534557420861695[41] = 1;
   out_41534557420861695[42] = 0;
   out_41534557420861695[43] = 0;
   out_41534557420861695[44] = 0;
   out_41534557420861695[45] = 0;
   out_41534557420861695[46] = 0;
   out_41534557420861695[47] = 0;
   out_41534557420861695[48] = 0;
   out_41534557420861695[49] = 0;
   out_41534557420861695[50] = 0;
   out_41534557420861695[51] = 0;
   out_41534557420861695[52] = 0;
   out_41534557420861695[53] = 0;
}
void h_14(double *state, double *unused, double *out_5599078925332714729) {
   out_5599078925332714729[0] = state[6];
   out_5599078925332714729[1] = state[7];
   out_5599078925332714729[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3688924909398078095) {
   out_3688924909398078095[0] = 0;
   out_3688924909398078095[1] = 0;
   out_3688924909398078095[2] = 0;
   out_3688924909398078095[3] = 0;
   out_3688924909398078095[4] = 0;
   out_3688924909398078095[5] = 0;
   out_3688924909398078095[6] = 1;
   out_3688924909398078095[7] = 0;
   out_3688924909398078095[8] = 0;
   out_3688924909398078095[9] = 0;
   out_3688924909398078095[10] = 0;
   out_3688924909398078095[11] = 0;
   out_3688924909398078095[12] = 0;
   out_3688924909398078095[13] = 0;
   out_3688924909398078095[14] = 0;
   out_3688924909398078095[15] = 0;
   out_3688924909398078095[16] = 0;
   out_3688924909398078095[17] = 0;
   out_3688924909398078095[18] = 0;
   out_3688924909398078095[19] = 0;
   out_3688924909398078095[20] = 0;
   out_3688924909398078095[21] = 0;
   out_3688924909398078095[22] = 0;
   out_3688924909398078095[23] = 0;
   out_3688924909398078095[24] = 0;
   out_3688924909398078095[25] = 1;
   out_3688924909398078095[26] = 0;
   out_3688924909398078095[27] = 0;
   out_3688924909398078095[28] = 0;
   out_3688924909398078095[29] = 0;
   out_3688924909398078095[30] = 0;
   out_3688924909398078095[31] = 0;
   out_3688924909398078095[32] = 0;
   out_3688924909398078095[33] = 0;
   out_3688924909398078095[34] = 0;
   out_3688924909398078095[35] = 0;
   out_3688924909398078095[36] = 0;
   out_3688924909398078095[37] = 0;
   out_3688924909398078095[38] = 0;
   out_3688924909398078095[39] = 0;
   out_3688924909398078095[40] = 0;
   out_3688924909398078095[41] = 0;
   out_3688924909398078095[42] = 0;
   out_3688924909398078095[43] = 0;
   out_3688924909398078095[44] = 1;
   out_3688924909398078095[45] = 0;
   out_3688924909398078095[46] = 0;
   out_3688924909398078095[47] = 0;
   out_3688924909398078095[48] = 0;
   out_3688924909398078095[49] = 0;
   out_3688924909398078095[50] = 0;
   out_3688924909398078095[51] = 0;
   out_3688924909398078095[52] = 0;
   out_3688924909398078095[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5543923555702989986) {
  err_fun(nom_x, delta_x, out_5543923555702989986);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8171878046525728238) {
  inv_err_fun(nom_x, true_x, out_8171878046525728238);
}
void pose_H_mod_fun(double *state, double *out_5690553283304626846) {
  H_mod_fun(state, out_5690553283304626846);
}
void pose_f_fun(double *state, double dt, double *out_5317158281057841296) {
  f_fun(state,  dt, out_5317158281057841296);
}
void pose_F_fun(double *state, double dt, double *out_34764116407898728) {
  F_fun(state,  dt, out_34764116407898728);
}
void pose_h_4(double *state, double *unused, double *out_2611058549638811197) {
  h_4(state, unused, out_2611058549638811197);
}
void pose_H_4(double *state, double *unused, double *out_3253808382753194496) {
  H_4(state, unused, out_3253808382753194496);
}
void pose_h_10(double *state, double *unused, double *out_8670807093231338393) {
  h_10(state, unused, out_8670807093231338393);
}
void pose_H_10(double *state, double *unused, double *out_718769444777682190) {
  H_10(state, unused, out_718769444777682190);
}
void pose_h_13(double *state, double *unused, double *out_4814072555028059760) {
  h_13(state, unused, out_4814072555028059760);
}
void pose_H_13(double *state, double *unused, double *out_41534557420861695) {
  H_13(state, unused, out_41534557420861695);
}
void pose_h_14(double *state, double *unused, double *out_5599078925332714729) {
  h_14(state, unused, out_5599078925332714729);
}
void pose_H_14(double *state, double *unused, double *out_3688924909398078095) {
  H_14(state, unused, out_3688924909398078095);
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
