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
void err_fun(double *nom_x, double *delta_x, double *out_7101503095265833649) {
   out_7101503095265833649[0] = delta_x[0] + nom_x[0];
   out_7101503095265833649[1] = delta_x[1] + nom_x[1];
   out_7101503095265833649[2] = delta_x[2] + nom_x[2];
   out_7101503095265833649[3] = delta_x[3] + nom_x[3];
   out_7101503095265833649[4] = delta_x[4] + nom_x[4];
   out_7101503095265833649[5] = delta_x[5] + nom_x[5];
   out_7101503095265833649[6] = delta_x[6] + nom_x[6];
   out_7101503095265833649[7] = delta_x[7] + nom_x[7];
   out_7101503095265833649[8] = delta_x[8] + nom_x[8];
   out_7101503095265833649[9] = delta_x[9] + nom_x[9];
   out_7101503095265833649[10] = delta_x[10] + nom_x[10];
   out_7101503095265833649[11] = delta_x[11] + nom_x[11];
   out_7101503095265833649[12] = delta_x[12] + nom_x[12];
   out_7101503095265833649[13] = delta_x[13] + nom_x[13];
   out_7101503095265833649[14] = delta_x[14] + nom_x[14];
   out_7101503095265833649[15] = delta_x[15] + nom_x[15];
   out_7101503095265833649[16] = delta_x[16] + nom_x[16];
   out_7101503095265833649[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4514359099843804277) {
   out_4514359099843804277[0] = -nom_x[0] + true_x[0];
   out_4514359099843804277[1] = -nom_x[1] + true_x[1];
   out_4514359099843804277[2] = -nom_x[2] + true_x[2];
   out_4514359099843804277[3] = -nom_x[3] + true_x[3];
   out_4514359099843804277[4] = -nom_x[4] + true_x[4];
   out_4514359099843804277[5] = -nom_x[5] + true_x[5];
   out_4514359099843804277[6] = -nom_x[6] + true_x[6];
   out_4514359099843804277[7] = -nom_x[7] + true_x[7];
   out_4514359099843804277[8] = -nom_x[8] + true_x[8];
   out_4514359099843804277[9] = -nom_x[9] + true_x[9];
   out_4514359099843804277[10] = -nom_x[10] + true_x[10];
   out_4514359099843804277[11] = -nom_x[11] + true_x[11];
   out_4514359099843804277[12] = -nom_x[12] + true_x[12];
   out_4514359099843804277[13] = -nom_x[13] + true_x[13];
   out_4514359099843804277[14] = -nom_x[14] + true_x[14];
   out_4514359099843804277[15] = -nom_x[15] + true_x[15];
   out_4514359099843804277[16] = -nom_x[16] + true_x[16];
   out_4514359099843804277[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7558013151580796863) {
   out_7558013151580796863[0] = 1.0;
   out_7558013151580796863[1] = 0.0;
   out_7558013151580796863[2] = 0.0;
   out_7558013151580796863[3] = 0.0;
   out_7558013151580796863[4] = 0.0;
   out_7558013151580796863[5] = 0.0;
   out_7558013151580796863[6] = 0.0;
   out_7558013151580796863[7] = 0.0;
   out_7558013151580796863[8] = 0.0;
   out_7558013151580796863[9] = 0.0;
   out_7558013151580796863[10] = 0.0;
   out_7558013151580796863[11] = 0.0;
   out_7558013151580796863[12] = 0.0;
   out_7558013151580796863[13] = 0.0;
   out_7558013151580796863[14] = 0.0;
   out_7558013151580796863[15] = 0.0;
   out_7558013151580796863[16] = 0.0;
   out_7558013151580796863[17] = 0.0;
   out_7558013151580796863[18] = 0.0;
   out_7558013151580796863[19] = 1.0;
   out_7558013151580796863[20] = 0.0;
   out_7558013151580796863[21] = 0.0;
   out_7558013151580796863[22] = 0.0;
   out_7558013151580796863[23] = 0.0;
   out_7558013151580796863[24] = 0.0;
   out_7558013151580796863[25] = 0.0;
   out_7558013151580796863[26] = 0.0;
   out_7558013151580796863[27] = 0.0;
   out_7558013151580796863[28] = 0.0;
   out_7558013151580796863[29] = 0.0;
   out_7558013151580796863[30] = 0.0;
   out_7558013151580796863[31] = 0.0;
   out_7558013151580796863[32] = 0.0;
   out_7558013151580796863[33] = 0.0;
   out_7558013151580796863[34] = 0.0;
   out_7558013151580796863[35] = 0.0;
   out_7558013151580796863[36] = 0.0;
   out_7558013151580796863[37] = 0.0;
   out_7558013151580796863[38] = 1.0;
   out_7558013151580796863[39] = 0.0;
   out_7558013151580796863[40] = 0.0;
   out_7558013151580796863[41] = 0.0;
   out_7558013151580796863[42] = 0.0;
   out_7558013151580796863[43] = 0.0;
   out_7558013151580796863[44] = 0.0;
   out_7558013151580796863[45] = 0.0;
   out_7558013151580796863[46] = 0.0;
   out_7558013151580796863[47] = 0.0;
   out_7558013151580796863[48] = 0.0;
   out_7558013151580796863[49] = 0.0;
   out_7558013151580796863[50] = 0.0;
   out_7558013151580796863[51] = 0.0;
   out_7558013151580796863[52] = 0.0;
   out_7558013151580796863[53] = 0.0;
   out_7558013151580796863[54] = 0.0;
   out_7558013151580796863[55] = 0.0;
   out_7558013151580796863[56] = 0.0;
   out_7558013151580796863[57] = 1.0;
   out_7558013151580796863[58] = 0.0;
   out_7558013151580796863[59] = 0.0;
   out_7558013151580796863[60] = 0.0;
   out_7558013151580796863[61] = 0.0;
   out_7558013151580796863[62] = 0.0;
   out_7558013151580796863[63] = 0.0;
   out_7558013151580796863[64] = 0.0;
   out_7558013151580796863[65] = 0.0;
   out_7558013151580796863[66] = 0.0;
   out_7558013151580796863[67] = 0.0;
   out_7558013151580796863[68] = 0.0;
   out_7558013151580796863[69] = 0.0;
   out_7558013151580796863[70] = 0.0;
   out_7558013151580796863[71] = 0.0;
   out_7558013151580796863[72] = 0.0;
   out_7558013151580796863[73] = 0.0;
   out_7558013151580796863[74] = 0.0;
   out_7558013151580796863[75] = 0.0;
   out_7558013151580796863[76] = 1.0;
   out_7558013151580796863[77] = 0.0;
   out_7558013151580796863[78] = 0.0;
   out_7558013151580796863[79] = 0.0;
   out_7558013151580796863[80] = 0.0;
   out_7558013151580796863[81] = 0.0;
   out_7558013151580796863[82] = 0.0;
   out_7558013151580796863[83] = 0.0;
   out_7558013151580796863[84] = 0.0;
   out_7558013151580796863[85] = 0.0;
   out_7558013151580796863[86] = 0.0;
   out_7558013151580796863[87] = 0.0;
   out_7558013151580796863[88] = 0.0;
   out_7558013151580796863[89] = 0.0;
   out_7558013151580796863[90] = 0.0;
   out_7558013151580796863[91] = 0.0;
   out_7558013151580796863[92] = 0.0;
   out_7558013151580796863[93] = 0.0;
   out_7558013151580796863[94] = 0.0;
   out_7558013151580796863[95] = 1.0;
   out_7558013151580796863[96] = 0.0;
   out_7558013151580796863[97] = 0.0;
   out_7558013151580796863[98] = 0.0;
   out_7558013151580796863[99] = 0.0;
   out_7558013151580796863[100] = 0.0;
   out_7558013151580796863[101] = 0.0;
   out_7558013151580796863[102] = 0.0;
   out_7558013151580796863[103] = 0.0;
   out_7558013151580796863[104] = 0.0;
   out_7558013151580796863[105] = 0.0;
   out_7558013151580796863[106] = 0.0;
   out_7558013151580796863[107] = 0.0;
   out_7558013151580796863[108] = 0.0;
   out_7558013151580796863[109] = 0.0;
   out_7558013151580796863[110] = 0.0;
   out_7558013151580796863[111] = 0.0;
   out_7558013151580796863[112] = 0.0;
   out_7558013151580796863[113] = 0.0;
   out_7558013151580796863[114] = 1.0;
   out_7558013151580796863[115] = 0.0;
   out_7558013151580796863[116] = 0.0;
   out_7558013151580796863[117] = 0.0;
   out_7558013151580796863[118] = 0.0;
   out_7558013151580796863[119] = 0.0;
   out_7558013151580796863[120] = 0.0;
   out_7558013151580796863[121] = 0.0;
   out_7558013151580796863[122] = 0.0;
   out_7558013151580796863[123] = 0.0;
   out_7558013151580796863[124] = 0.0;
   out_7558013151580796863[125] = 0.0;
   out_7558013151580796863[126] = 0.0;
   out_7558013151580796863[127] = 0.0;
   out_7558013151580796863[128] = 0.0;
   out_7558013151580796863[129] = 0.0;
   out_7558013151580796863[130] = 0.0;
   out_7558013151580796863[131] = 0.0;
   out_7558013151580796863[132] = 0.0;
   out_7558013151580796863[133] = 1.0;
   out_7558013151580796863[134] = 0.0;
   out_7558013151580796863[135] = 0.0;
   out_7558013151580796863[136] = 0.0;
   out_7558013151580796863[137] = 0.0;
   out_7558013151580796863[138] = 0.0;
   out_7558013151580796863[139] = 0.0;
   out_7558013151580796863[140] = 0.0;
   out_7558013151580796863[141] = 0.0;
   out_7558013151580796863[142] = 0.0;
   out_7558013151580796863[143] = 0.0;
   out_7558013151580796863[144] = 0.0;
   out_7558013151580796863[145] = 0.0;
   out_7558013151580796863[146] = 0.0;
   out_7558013151580796863[147] = 0.0;
   out_7558013151580796863[148] = 0.0;
   out_7558013151580796863[149] = 0.0;
   out_7558013151580796863[150] = 0.0;
   out_7558013151580796863[151] = 0.0;
   out_7558013151580796863[152] = 1.0;
   out_7558013151580796863[153] = 0.0;
   out_7558013151580796863[154] = 0.0;
   out_7558013151580796863[155] = 0.0;
   out_7558013151580796863[156] = 0.0;
   out_7558013151580796863[157] = 0.0;
   out_7558013151580796863[158] = 0.0;
   out_7558013151580796863[159] = 0.0;
   out_7558013151580796863[160] = 0.0;
   out_7558013151580796863[161] = 0.0;
   out_7558013151580796863[162] = 0.0;
   out_7558013151580796863[163] = 0.0;
   out_7558013151580796863[164] = 0.0;
   out_7558013151580796863[165] = 0.0;
   out_7558013151580796863[166] = 0.0;
   out_7558013151580796863[167] = 0.0;
   out_7558013151580796863[168] = 0.0;
   out_7558013151580796863[169] = 0.0;
   out_7558013151580796863[170] = 0.0;
   out_7558013151580796863[171] = 1.0;
   out_7558013151580796863[172] = 0.0;
   out_7558013151580796863[173] = 0.0;
   out_7558013151580796863[174] = 0.0;
   out_7558013151580796863[175] = 0.0;
   out_7558013151580796863[176] = 0.0;
   out_7558013151580796863[177] = 0.0;
   out_7558013151580796863[178] = 0.0;
   out_7558013151580796863[179] = 0.0;
   out_7558013151580796863[180] = 0.0;
   out_7558013151580796863[181] = 0.0;
   out_7558013151580796863[182] = 0.0;
   out_7558013151580796863[183] = 0.0;
   out_7558013151580796863[184] = 0.0;
   out_7558013151580796863[185] = 0.0;
   out_7558013151580796863[186] = 0.0;
   out_7558013151580796863[187] = 0.0;
   out_7558013151580796863[188] = 0.0;
   out_7558013151580796863[189] = 0.0;
   out_7558013151580796863[190] = 1.0;
   out_7558013151580796863[191] = 0.0;
   out_7558013151580796863[192] = 0.0;
   out_7558013151580796863[193] = 0.0;
   out_7558013151580796863[194] = 0.0;
   out_7558013151580796863[195] = 0.0;
   out_7558013151580796863[196] = 0.0;
   out_7558013151580796863[197] = 0.0;
   out_7558013151580796863[198] = 0.0;
   out_7558013151580796863[199] = 0.0;
   out_7558013151580796863[200] = 0.0;
   out_7558013151580796863[201] = 0.0;
   out_7558013151580796863[202] = 0.0;
   out_7558013151580796863[203] = 0.0;
   out_7558013151580796863[204] = 0.0;
   out_7558013151580796863[205] = 0.0;
   out_7558013151580796863[206] = 0.0;
   out_7558013151580796863[207] = 0.0;
   out_7558013151580796863[208] = 0.0;
   out_7558013151580796863[209] = 1.0;
   out_7558013151580796863[210] = 0.0;
   out_7558013151580796863[211] = 0.0;
   out_7558013151580796863[212] = 0.0;
   out_7558013151580796863[213] = 0.0;
   out_7558013151580796863[214] = 0.0;
   out_7558013151580796863[215] = 0.0;
   out_7558013151580796863[216] = 0.0;
   out_7558013151580796863[217] = 0.0;
   out_7558013151580796863[218] = 0.0;
   out_7558013151580796863[219] = 0.0;
   out_7558013151580796863[220] = 0.0;
   out_7558013151580796863[221] = 0.0;
   out_7558013151580796863[222] = 0.0;
   out_7558013151580796863[223] = 0.0;
   out_7558013151580796863[224] = 0.0;
   out_7558013151580796863[225] = 0.0;
   out_7558013151580796863[226] = 0.0;
   out_7558013151580796863[227] = 0.0;
   out_7558013151580796863[228] = 1.0;
   out_7558013151580796863[229] = 0.0;
   out_7558013151580796863[230] = 0.0;
   out_7558013151580796863[231] = 0.0;
   out_7558013151580796863[232] = 0.0;
   out_7558013151580796863[233] = 0.0;
   out_7558013151580796863[234] = 0.0;
   out_7558013151580796863[235] = 0.0;
   out_7558013151580796863[236] = 0.0;
   out_7558013151580796863[237] = 0.0;
   out_7558013151580796863[238] = 0.0;
   out_7558013151580796863[239] = 0.0;
   out_7558013151580796863[240] = 0.0;
   out_7558013151580796863[241] = 0.0;
   out_7558013151580796863[242] = 0.0;
   out_7558013151580796863[243] = 0.0;
   out_7558013151580796863[244] = 0.0;
   out_7558013151580796863[245] = 0.0;
   out_7558013151580796863[246] = 0.0;
   out_7558013151580796863[247] = 1.0;
   out_7558013151580796863[248] = 0.0;
   out_7558013151580796863[249] = 0.0;
   out_7558013151580796863[250] = 0.0;
   out_7558013151580796863[251] = 0.0;
   out_7558013151580796863[252] = 0.0;
   out_7558013151580796863[253] = 0.0;
   out_7558013151580796863[254] = 0.0;
   out_7558013151580796863[255] = 0.0;
   out_7558013151580796863[256] = 0.0;
   out_7558013151580796863[257] = 0.0;
   out_7558013151580796863[258] = 0.0;
   out_7558013151580796863[259] = 0.0;
   out_7558013151580796863[260] = 0.0;
   out_7558013151580796863[261] = 0.0;
   out_7558013151580796863[262] = 0.0;
   out_7558013151580796863[263] = 0.0;
   out_7558013151580796863[264] = 0.0;
   out_7558013151580796863[265] = 0.0;
   out_7558013151580796863[266] = 1.0;
   out_7558013151580796863[267] = 0.0;
   out_7558013151580796863[268] = 0.0;
   out_7558013151580796863[269] = 0.0;
   out_7558013151580796863[270] = 0.0;
   out_7558013151580796863[271] = 0.0;
   out_7558013151580796863[272] = 0.0;
   out_7558013151580796863[273] = 0.0;
   out_7558013151580796863[274] = 0.0;
   out_7558013151580796863[275] = 0.0;
   out_7558013151580796863[276] = 0.0;
   out_7558013151580796863[277] = 0.0;
   out_7558013151580796863[278] = 0.0;
   out_7558013151580796863[279] = 0.0;
   out_7558013151580796863[280] = 0.0;
   out_7558013151580796863[281] = 0.0;
   out_7558013151580796863[282] = 0.0;
   out_7558013151580796863[283] = 0.0;
   out_7558013151580796863[284] = 0.0;
   out_7558013151580796863[285] = 1.0;
   out_7558013151580796863[286] = 0.0;
   out_7558013151580796863[287] = 0.0;
   out_7558013151580796863[288] = 0.0;
   out_7558013151580796863[289] = 0.0;
   out_7558013151580796863[290] = 0.0;
   out_7558013151580796863[291] = 0.0;
   out_7558013151580796863[292] = 0.0;
   out_7558013151580796863[293] = 0.0;
   out_7558013151580796863[294] = 0.0;
   out_7558013151580796863[295] = 0.0;
   out_7558013151580796863[296] = 0.0;
   out_7558013151580796863[297] = 0.0;
   out_7558013151580796863[298] = 0.0;
   out_7558013151580796863[299] = 0.0;
   out_7558013151580796863[300] = 0.0;
   out_7558013151580796863[301] = 0.0;
   out_7558013151580796863[302] = 0.0;
   out_7558013151580796863[303] = 0.0;
   out_7558013151580796863[304] = 1.0;
   out_7558013151580796863[305] = 0.0;
   out_7558013151580796863[306] = 0.0;
   out_7558013151580796863[307] = 0.0;
   out_7558013151580796863[308] = 0.0;
   out_7558013151580796863[309] = 0.0;
   out_7558013151580796863[310] = 0.0;
   out_7558013151580796863[311] = 0.0;
   out_7558013151580796863[312] = 0.0;
   out_7558013151580796863[313] = 0.0;
   out_7558013151580796863[314] = 0.0;
   out_7558013151580796863[315] = 0.0;
   out_7558013151580796863[316] = 0.0;
   out_7558013151580796863[317] = 0.0;
   out_7558013151580796863[318] = 0.0;
   out_7558013151580796863[319] = 0.0;
   out_7558013151580796863[320] = 0.0;
   out_7558013151580796863[321] = 0.0;
   out_7558013151580796863[322] = 0.0;
   out_7558013151580796863[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6874989583183873730) {
   out_6874989583183873730[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6874989583183873730[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6874989583183873730[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6874989583183873730[3] = dt*state[12] + state[3];
   out_6874989583183873730[4] = dt*state[13] + state[4];
   out_6874989583183873730[5] = dt*state[14] + state[5];
   out_6874989583183873730[6] = state[6];
   out_6874989583183873730[7] = state[7];
   out_6874989583183873730[8] = state[8];
   out_6874989583183873730[9] = state[9];
   out_6874989583183873730[10] = state[10];
   out_6874989583183873730[11] = state[11];
   out_6874989583183873730[12] = state[12];
   out_6874989583183873730[13] = state[13];
   out_6874989583183873730[14] = state[14];
   out_6874989583183873730[15] = state[15];
   out_6874989583183873730[16] = state[16];
   out_6874989583183873730[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2414486911096174000) {
   out_2414486911096174000[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2414486911096174000[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2414486911096174000[2] = 0;
   out_2414486911096174000[3] = 0;
   out_2414486911096174000[4] = 0;
   out_2414486911096174000[5] = 0;
   out_2414486911096174000[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2414486911096174000[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2414486911096174000[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2414486911096174000[9] = 0;
   out_2414486911096174000[10] = 0;
   out_2414486911096174000[11] = 0;
   out_2414486911096174000[12] = 0;
   out_2414486911096174000[13] = 0;
   out_2414486911096174000[14] = 0;
   out_2414486911096174000[15] = 0;
   out_2414486911096174000[16] = 0;
   out_2414486911096174000[17] = 0;
   out_2414486911096174000[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2414486911096174000[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2414486911096174000[20] = 0;
   out_2414486911096174000[21] = 0;
   out_2414486911096174000[22] = 0;
   out_2414486911096174000[23] = 0;
   out_2414486911096174000[24] = 0;
   out_2414486911096174000[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2414486911096174000[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2414486911096174000[27] = 0;
   out_2414486911096174000[28] = 0;
   out_2414486911096174000[29] = 0;
   out_2414486911096174000[30] = 0;
   out_2414486911096174000[31] = 0;
   out_2414486911096174000[32] = 0;
   out_2414486911096174000[33] = 0;
   out_2414486911096174000[34] = 0;
   out_2414486911096174000[35] = 0;
   out_2414486911096174000[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2414486911096174000[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2414486911096174000[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2414486911096174000[39] = 0;
   out_2414486911096174000[40] = 0;
   out_2414486911096174000[41] = 0;
   out_2414486911096174000[42] = 0;
   out_2414486911096174000[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2414486911096174000[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2414486911096174000[45] = 0;
   out_2414486911096174000[46] = 0;
   out_2414486911096174000[47] = 0;
   out_2414486911096174000[48] = 0;
   out_2414486911096174000[49] = 0;
   out_2414486911096174000[50] = 0;
   out_2414486911096174000[51] = 0;
   out_2414486911096174000[52] = 0;
   out_2414486911096174000[53] = 0;
   out_2414486911096174000[54] = 0;
   out_2414486911096174000[55] = 0;
   out_2414486911096174000[56] = 0;
   out_2414486911096174000[57] = 1;
   out_2414486911096174000[58] = 0;
   out_2414486911096174000[59] = 0;
   out_2414486911096174000[60] = 0;
   out_2414486911096174000[61] = 0;
   out_2414486911096174000[62] = 0;
   out_2414486911096174000[63] = 0;
   out_2414486911096174000[64] = 0;
   out_2414486911096174000[65] = 0;
   out_2414486911096174000[66] = dt;
   out_2414486911096174000[67] = 0;
   out_2414486911096174000[68] = 0;
   out_2414486911096174000[69] = 0;
   out_2414486911096174000[70] = 0;
   out_2414486911096174000[71] = 0;
   out_2414486911096174000[72] = 0;
   out_2414486911096174000[73] = 0;
   out_2414486911096174000[74] = 0;
   out_2414486911096174000[75] = 0;
   out_2414486911096174000[76] = 1;
   out_2414486911096174000[77] = 0;
   out_2414486911096174000[78] = 0;
   out_2414486911096174000[79] = 0;
   out_2414486911096174000[80] = 0;
   out_2414486911096174000[81] = 0;
   out_2414486911096174000[82] = 0;
   out_2414486911096174000[83] = 0;
   out_2414486911096174000[84] = 0;
   out_2414486911096174000[85] = dt;
   out_2414486911096174000[86] = 0;
   out_2414486911096174000[87] = 0;
   out_2414486911096174000[88] = 0;
   out_2414486911096174000[89] = 0;
   out_2414486911096174000[90] = 0;
   out_2414486911096174000[91] = 0;
   out_2414486911096174000[92] = 0;
   out_2414486911096174000[93] = 0;
   out_2414486911096174000[94] = 0;
   out_2414486911096174000[95] = 1;
   out_2414486911096174000[96] = 0;
   out_2414486911096174000[97] = 0;
   out_2414486911096174000[98] = 0;
   out_2414486911096174000[99] = 0;
   out_2414486911096174000[100] = 0;
   out_2414486911096174000[101] = 0;
   out_2414486911096174000[102] = 0;
   out_2414486911096174000[103] = 0;
   out_2414486911096174000[104] = dt;
   out_2414486911096174000[105] = 0;
   out_2414486911096174000[106] = 0;
   out_2414486911096174000[107] = 0;
   out_2414486911096174000[108] = 0;
   out_2414486911096174000[109] = 0;
   out_2414486911096174000[110] = 0;
   out_2414486911096174000[111] = 0;
   out_2414486911096174000[112] = 0;
   out_2414486911096174000[113] = 0;
   out_2414486911096174000[114] = 1;
   out_2414486911096174000[115] = 0;
   out_2414486911096174000[116] = 0;
   out_2414486911096174000[117] = 0;
   out_2414486911096174000[118] = 0;
   out_2414486911096174000[119] = 0;
   out_2414486911096174000[120] = 0;
   out_2414486911096174000[121] = 0;
   out_2414486911096174000[122] = 0;
   out_2414486911096174000[123] = 0;
   out_2414486911096174000[124] = 0;
   out_2414486911096174000[125] = 0;
   out_2414486911096174000[126] = 0;
   out_2414486911096174000[127] = 0;
   out_2414486911096174000[128] = 0;
   out_2414486911096174000[129] = 0;
   out_2414486911096174000[130] = 0;
   out_2414486911096174000[131] = 0;
   out_2414486911096174000[132] = 0;
   out_2414486911096174000[133] = 1;
   out_2414486911096174000[134] = 0;
   out_2414486911096174000[135] = 0;
   out_2414486911096174000[136] = 0;
   out_2414486911096174000[137] = 0;
   out_2414486911096174000[138] = 0;
   out_2414486911096174000[139] = 0;
   out_2414486911096174000[140] = 0;
   out_2414486911096174000[141] = 0;
   out_2414486911096174000[142] = 0;
   out_2414486911096174000[143] = 0;
   out_2414486911096174000[144] = 0;
   out_2414486911096174000[145] = 0;
   out_2414486911096174000[146] = 0;
   out_2414486911096174000[147] = 0;
   out_2414486911096174000[148] = 0;
   out_2414486911096174000[149] = 0;
   out_2414486911096174000[150] = 0;
   out_2414486911096174000[151] = 0;
   out_2414486911096174000[152] = 1;
   out_2414486911096174000[153] = 0;
   out_2414486911096174000[154] = 0;
   out_2414486911096174000[155] = 0;
   out_2414486911096174000[156] = 0;
   out_2414486911096174000[157] = 0;
   out_2414486911096174000[158] = 0;
   out_2414486911096174000[159] = 0;
   out_2414486911096174000[160] = 0;
   out_2414486911096174000[161] = 0;
   out_2414486911096174000[162] = 0;
   out_2414486911096174000[163] = 0;
   out_2414486911096174000[164] = 0;
   out_2414486911096174000[165] = 0;
   out_2414486911096174000[166] = 0;
   out_2414486911096174000[167] = 0;
   out_2414486911096174000[168] = 0;
   out_2414486911096174000[169] = 0;
   out_2414486911096174000[170] = 0;
   out_2414486911096174000[171] = 1;
   out_2414486911096174000[172] = 0;
   out_2414486911096174000[173] = 0;
   out_2414486911096174000[174] = 0;
   out_2414486911096174000[175] = 0;
   out_2414486911096174000[176] = 0;
   out_2414486911096174000[177] = 0;
   out_2414486911096174000[178] = 0;
   out_2414486911096174000[179] = 0;
   out_2414486911096174000[180] = 0;
   out_2414486911096174000[181] = 0;
   out_2414486911096174000[182] = 0;
   out_2414486911096174000[183] = 0;
   out_2414486911096174000[184] = 0;
   out_2414486911096174000[185] = 0;
   out_2414486911096174000[186] = 0;
   out_2414486911096174000[187] = 0;
   out_2414486911096174000[188] = 0;
   out_2414486911096174000[189] = 0;
   out_2414486911096174000[190] = 1;
   out_2414486911096174000[191] = 0;
   out_2414486911096174000[192] = 0;
   out_2414486911096174000[193] = 0;
   out_2414486911096174000[194] = 0;
   out_2414486911096174000[195] = 0;
   out_2414486911096174000[196] = 0;
   out_2414486911096174000[197] = 0;
   out_2414486911096174000[198] = 0;
   out_2414486911096174000[199] = 0;
   out_2414486911096174000[200] = 0;
   out_2414486911096174000[201] = 0;
   out_2414486911096174000[202] = 0;
   out_2414486911096174000[203] = 0;
   out_2414486911096174000[204] = 0;
   out_2414486911096174000[205] = 0;
   out_2414486911096174000[206] = 0;
   out_2414486911096174000[207] = 0;
   out_2414486911096174000[208] = 0;
   out_2414486911096174000[209] = 1;
   out_2414486911096174000[210] = 0;
   out_2414486911096174000[211] = 0;
   out_2414486911096174000[212] = 0;
   out_2414486911096174000[213] = 0;
   out_2414486911096174000[214] = 0;
   out_2414486911096174000[215] = 0;
   out_2414486911096174000[216] = 0;
   out_2414486911096174000[217] = 0;
   out_2414486911096174000[218] = 0;
   out_2414486911096174000[219] = 0;
   out_2414486911096174000[220] = 0;
   out_2414486911096174000[221] = 0;
   out_2414486911096174000[222] = 0;
   out_2414486911096174000[223] = 0;
   out_2414486911096174000[224] = 0;
   out_2414486911096174000[225] = 0;
   out_2414486911096174000[226] = 0;
   out_2414486911096174000[227] = 0;
   out_2414486911096174000[228] = 1;
   out_2414486911096174000[229] = 0;
   out_2414486911096174000[230] = 0;
   out_2414486911096174000[231] = 0;
   out_2414486911096174000[232] = 0;
   out_2414486911096174000[233] = 0;
   out_2414486911096174000[234] = 0;
   out_2414486911096174000[235] = 0;
   out_2414486911096174000[236] = 0;
   out_2414486911096174000[237] = 0;
   out_2414486911096174000[238] = 0;
   out_2414486911096174000[239] = 0;
   out_2414486911096174000[240] = 0;
   out_2414486911096174000[241] = 0;
   out_2414486911096174000[242] = 0;
   out_2414486911096174000[243] = 0;
   out_2414486911096174000[244] = 0;
   out_2414486911096174000[245] = 0;
   out_2414486911096174000[246] = 0;
   out_2414486911096174000[247] = 1;
   out_2414486911096174000[248] = 0;
   out_2414486911096174000[249] = 0;
   out_2414486911096174000[250] = 0;
   out_2414486911096174000[251] = 0;
   out_2414486911096174000[252] = 0;
   out_2414486911096174000[253] = 0;
   out_2414486911096174000[254] = 0;
   out_2414486911096174000[255] = 0;
   out_2414486911096174000[256] = 0;
   out_2414486911096174000[257] = 0;
   out_2414486911096174000[258] = 0;
   out_2414486911096174000[259] = 0;
   out_2414486911096174000[260] = 0;
   out_2414486911096174000[261] = 0;
   out_2414486911096174000[262] = 0;
   out_2414486911096174000[263] = 0;
   out_2414486911096174000[264] = 0;
   out_2414486911096174000[265] = 0;
   out_2414486911096174000[266] = 1;
   out_2414486911096174000[267] = 0;
   out_2414486911096174000[268] = 0;
   out_2414486911096174000[269] = 0;
   out_2414486911096174000[270] = 0;
   out_2414486911096174000[271] = 0;
   out_2414486911096174000[272] = 0;
   out_2414486911096174000[273] = 0;
   out_2414486911096174000[274] = 0;
   out_2414486911096174000[275] = 0;
   out_2414486911096174000[276] = 0;
   out_2414486911096174000[277] = 0;
   out_2414486911096174000[278] = 0;
   out_2414486911096174000[279] = 0;
   out_2414486911096174000[280] = 0;
   out_2414486911096174000[281] = 0;
   out_2414486911096174000[282] = 0;
   out_2414486911096174000[283] = 0;
   out_2414486911096174000[284] = 0;
   out_2414486911096174000[285] = 1;
   out_2414486911096174000[286] = 0;
   out_2414486911096174000[287] = 0;
   out_2414486911096174000[288] = 0;
   out_2414486911096174000[289] = 0;
   out_2414486911096174000[290] = 0;
   out_2414486911096174000[291] = 0;
   out_2414486911096174000[292] = 0;
   out_2414486911096174000[293] = 0;
   out_2414486911096174000[294] = 0;
   out_2414486911096174000[295] = 0;
   out_2414486911096174000[296] = 0;
   out_2414486911096174000[297] = 0;
   out_2414486911096174000[298] = 0;
   out_2414486911096174000[299] = 0;
   out_2414486911096174000[300] = 0;
   out_2414486911096174000[301] = 0;
   out_2414486911096174000[302] = 0;
   out_2414486911096174000[303] = 0;
   out_2414486911096174000[304] = 1;
   out_2414486911096174000[305] = 0;
   out_2414486911096174000[306] = 0;
   out_2414486911096174000[307] = 0;
   out_2414486911096174000[308] = 0;
   out_2414486911096174000[309] = 0;
   out_2414486911096174000[310] = 0;
   out_2414486911096174000[311] = 0;
   out_2414486911096174000[312] = 0;
   out_2414486911096174000[313] = 0;
   out_2414486911096174000[314] = 0;
   out_2414486911096174000[315] = 0;
   out_2414486911096174000[316] = 0;
   out_2414486911096174000[317] = 0;
   out_2414486911096174000[318] = 0;
   out_2414486911096174000[319] = 0;
   out_2414486911096174000[320] = 0;
   out_2414486911096174000[321] = 0;
   out_2414486911096174000[322] = 0;
   out_2414486911096174000[323] = 1;
}
void h_4(double *state, double *unused, double *out_2032881575968680861) {
   out_2032881575968680861[0] = state[6] + state[9];
   out_2032881575968680861[1] = state[7] + state[10];
   out_2032881575968680861[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8312174153635509470) {
   out_8312174153635509470[0] = 0;
   out_8312174153635509470[1] = 0;
   out_8312174153635509470[2] = 0;
   out_8312174153635509470[3] = 0;
   out_8312174153635509470[4] = 0;
   out_8312174153635509470[5] = 0;
   out_8312174153635509470[6] = 1;
   out_8312174153635509470[7] = 0;
   out_8312174153635509470[8] = 0;
   out_8312174153635509470[9] = 1;
   out_8312174153635509470[10] = 0;
   out_8312174153635509470[11] = 0;
   out_8312174153635509470[12] = 0;
   out_8312174153635509470[13] = 0;
   out_8312174153635509470[14] = 0;
   out_8312174153635509470[15] = 0;
   out_8312174153635509470[16] = 0;
   out_8312174153635509470[17] = 0;
   out_8312174153635509470[18] = 0;
   out_8312174153635509470[19] = 0;
   out_8312174153635509470[20] = 0;
   out_8312174153635509470[21] = 0;
   out_8312174153635509470[22] = 0;
   out_8312174153635509470[23] = 0;
   out_8312174153635509470[24] = 0;
   out_8312174153635509470[25] = 1;
   out_8312174153635509470[26] = 0;
   out_8312174153635509470[27] = 0;
   out_8312174153635509470[28] = 1;
   out_8312174153635509470[29] = 0;
   out_8312174153635509470[30] = 0;
   out_8312174153635509470[31] = 0;
   out_8312174153635509470[32] = 0;
   out_8312174153635509470[33] = 0;
   out_8312174153635509470[34] = 0;
   out_8312174153635509470[35] = 0;
   out_8312174153635509470[36] = 0;
   out_8312174153635509470[37] = 0;
   out_8312174153635509470[38] = 0;
   out_8312174153635509470[39] = 0;
   out_8312174153635509470[40] = 0;
   out_8312174153635509470[41] = 0;
   out_8312174153635509470[42] = 0;
   out_8312174153635509470[43] = 0;
   out_8312174153635509470[44] = 1;
   out_8312174153635509470[45] = 0;
   out_8312174153635509470[46] = 0;
   out_8312174153635509470[47] = 1;
   out_8312174153635509470[48] = 0;
   out_8312174153635509470[49] = 0;
   out_8312174153635509470[50] = 0;
   out_8312174153635509470[51] = 0;
   out_8312174153635509470[52] = 0;
   out_8312174153635509470[53] = 0;
}
void h_10(double *state, double *unused, double *out_6246501970919422236) {
   out_6246501970919422236[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6246501970919422236[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6246501970919422236[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_9105171975845846865) {
   out_9105171975845846865[0] = 0;
   out_9105171975845846865[1] = 9.8100000000000005*cos(state[1]);
   out_9105171975845846865[2] = 0;
   out_9105171975845846865[3] = 0;
   out_9105171975845846865[4] = -state[8];
   out_9105171975845846865[5] = state[7];
   out_9105171975845846865[6] = 0;
   out_9105171975845846865[7] = state[5];
   out_9105171975845846865[8] = -state[4];
   out_9105171975845846865[9] = 0;
   out_9105171975845846865[10] = 0;
   out_9105171975845846865[11] = 0;
   out_9105171975845846865[12] = 1;
   out_9105171975845846865[13] = 0;
   out_9105171975845846865[14] = 0;
   out_9105171975845846865[15] = 1;
   out_9105171975845846865[16] = 0;
   out_9105171975845846865[17] = 0;
   out_9105171975845846865[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_9105171975845846865[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_9105171975845846865[20] = 0;
   out_9105171975845846865[21] = state[8];
   out_9105171975845846865[22] = 0;
   out_9105171975845846865[23] = -state[6];
   out_9105171975845846865[24] = -state[5];
   out_9105171975845846865[25] = 0;
   out_9105171975845846865[26] = state[3];
   out_9105171975845846865[27] = 0;
   out_9105171975845846865[28] = 0;
   out_9105171975845846865[29] = 0;
   out_9105171975845846865[30] = 0;
   out_9105171975845846865[31] = 1;
   out_9105171975845846865[32] = 0;
   out_9105171975845846865[33] = 0;
   out_9105171975845846865[34] = 1;
   out_9105171975845846865[35] = 0;
   out_9105171975845846865[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_9105171975845846865[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_9105171975845846865[38] = 0;
   out_9105171975845846865[39] = -state[7];
   out_9105171975845846865[40] = state[6];
   out_9105171975845846865[41] = 0;
   out_9105171975845846865[42] = state[4];
   out_9105171975845846865[43] = -state[3];
   out_9105171975845846865[44] = 0;
   out_9105171975845846865[45] = 0;
   out_9105171975845846865[46] = 0;
   out_9105171975845846865[47] = 0;
   out_9105171975845846865[48] = 0;
   out_9105171975845846865[49] = 0;
   out_9105171975845846865[50] = 1;
   out_9105171975845846865[51] = 0;
   out_9105171975845846865[52] = 0;
   out_9105171975845846865[53] = 1;
}
void h_13(double *state, double *unused, double *out_5690258237608804476) {
   out_5690258237608804476[0] = state[3];
   out_5690258237608804476[1] = state[4];
   out_5690258237608804476[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2523938711757341217) {
   out_2523938711757341217[0] = 0;
   out_2523938711757341217[1] = 0;
   out_2523938711757341217[2] = 0;
   out_2523938711757341217[3] = 1;
   out_2523938711757341217[4] = 0;
   out_2523938711757341217[5] = 0;
   out_2523938711757341217[6] = 0;
   out_2523938711757341217[7] = 0;
   out_2523938711757341217[8] = 0;
   out_2523938711757341217[9] = 0;
   out_2523938711757341217[10] = 0;
   out_2523938711757341217[11] = 0;
   out_2523938711757341217[12] = 0;
   out_2523938711757341217[13] = 0;
   out_2523938711757341217[14] = 0;
   out_2523938711757341217[15] = 0;
   out_2523938711757341217[16] = 0;
   out_2523938711757341217[17] = 0;
   out_2523938711757341217[18] = 0;
   out_2523938711757341217[19] = 0;
   out_2523938711757341217[20] = 0;
   out_2523938711757341217[21] = 0;
   out_2523938711757341217[22] = 1;
   out_2523938711757341217[23] = 0;
   out_2523938711757341217[24] = 0;
   out_2523938711757341217[25] = 0;
   out_2523938711757341217[26] = 0;
   out_2523938711757341217[27] = 0;
   out_2523938711757341217[28] = 0;
   out_2523938711757341217[29] = 0;
   out_2523938711757341217[30] = 0;
   out_2523938711757341217[31] = 0;
   out_2523938711757341217[32] = 0;
   out_2523938711757341217[33] = 0;
   out_2523938711757341217[34] = 0;
   out_2523938711757341217[35] = 0;
   out_2523938711757341217[36] = 0;
   out_2523938711757341217[37] = 0;
   out_2523938711757341217[38] = 0;
   out_2523938711757341217[39] = 0;
   out_2523938711757341217[40] = 0;
   out_2523938711757341217[41] = 1;
   out_2523938711757341217[42] = 0;
   out_2523938711757341217[43] = 0;
   out_2523938711757341217[44] = 0;
   out_2523938711757341217[45] = 0;
   out_2523938711757341217[46] = 0;
   out_2523938711757341217[47] = 0;
   out_2523938711757341217[48] = 0;
   out_2523938711757341217[49] = 0;
   out_2523938711757341217[50] = 0;
   out_2523938711757341217[51] = 0;
   out_2523938711757341217[52] = 0;
   out_2523938711757341217[53] = 0;
}
void h_14(double *state, double *unused, double *out_4651254816825442403) {
   out_4651254816825442403[0] = state[6];
   out_4651254816825442403[1] = state[7];
   out_4651254816825442403[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6171329063734557617) {
   out_6171329063734557617[0] = 0;
   out_6171329063734557617[1] = 0;
   out_6171329063734557617[2] = 0;
   out_6171329063734557617[3] = 0;
   out_6171329063734557617[4] = 0;
   out_6171329063734557617[5] = 0;
   out_6171329063734557617[6] = 1;
   out_6171329063734557617[7] = 0;
   out_6171329063734557617[8] = 0;
   out_6171329063734557617[9] = 0;
   out_6171329063734557617[10] = 0;
   out_6171329063734557617[11] = 0;
   out_6171329063734557617[12] = 0;
   out_6171329063734557617[13] = 0;
   out_6171329063734557617[14] = 0;
   out_6171329063734557617[15] = 0;
   out_6171329063734557617[16] = 0;
   out_6171329063734557617[17] = 0;
   out_6171329063734557617[18] = 0;
   out_6171329063734557617[19] = 0;
   out_6171329063734557617[20] = 0;
   out_6171329063734557617[21] = 0;
   out_6171329063734557617[22] = 0;
   out_6171329063734557617[23] = 0;
   out_6171329063734557617[24] = 0;
   out_6171329063734557617[25] = 1;
   out_6171329063734557617[26] = 0;
   out_6171329063734557617[27] = 0;
   out_6171329063734557617[28] = 0;
   out_6171329063734557617[29] = 0;
   out_6171329063734557617[30] = 0;
   out_6171329063734557617[31] = 0;
   out_6171329063734557617[32] = 0;
   out_6171329063734557617[33] = 0;
   out_6171329063734557617[34] = 0;
   out_6171329063734557617[35] = 0;
   out_6171329063734557617[36] = 0;
   out_6171329063734557617[37] = 0;
   out_6171329063734557617[38] = 0;
   out_6171329063734557617[39] = 0;
   out_6171329063734557617[40] = 0;
   out_6171329063734557617[41] = 0;
   out_6171329063734557617[42] = 0;
   out_6171329063734557617[43] = 0;
   out_6171329063734557617[44] = 1;
   out_6171329063734557617[45] = 0;
   out_6171329063734557617[46] = 0;
   out_6171329063734557617[47] = 0;
   out_6171329063734557617[48] = 0;
   out_6171329063734557617[49] = 0;
   out_6171329063734557617[50] = 0;
   out_6171329063734557617[51] = 0;
   out_6171329063734557617[52] = 0;
   out_6171329063734557617[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7101503095265833649) {
  err_fun(nom_x, delta_x, out_7101503095265833649);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4514359099843804277) {
  inv_err_fun(nom_x, true_x, out_4514359099843804277);
}
void pose_H_mod_fun(double *state, double *out_7558013151580796863) {
  H_mod_fun(state, out_7558013151580796863);
}
void pose_f_fun(double *state, double dt, double *out_6874989583183873730) {
  f_fun(state,  dt, out_6874989583183873730);
}
void pose_F_fun(double *state, double dt, double *out_2414486911096174000) {
  F_fun(state,  dt, out_2414486911096174000);
}
void pose_h_4(double *state, double *unused, double *out_2032881575968680861) {
  h_4(state, unused, out_2032881575968680861);
}
void pose_H_4(double *state, double *unused, double *out_8312174153635509470) {
  H_4(state, unused, out_8312174153635509470);
}
void pose_h_10(double *state, double *unused, double *out_6246501970919422236) {
  h_10(state, unused, out_6246501970919422236);
}
void pose_H_10(double *state, double *unused, double *out_9105171975845846865) {
  H_10(state, unused, out_9105171975845846865);
}
void pose_h_13(double *state, double *unused, double *out_5690258237608804476) {
  h_13(state, unused, out_5690258237608804476);
}
void pose_H_13(double *state, double *unused, double *out_2523938711757341217) {
  H_13(state, unused, out_2523938711757341217);
}
void pose_h_14(double *state, double *unused, double *out_4651254816825442403) {
  h_14(state, unused, out_4651254816825442403);
}
void pose_H_14(double *state, double *unused, double *out_6171329063734557617) {
  H_14(state, unused, out_6171329063734557617);
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
