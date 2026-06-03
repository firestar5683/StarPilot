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
void err_fun(double *nom_x, double *delta_x, double *out_8753495689455606364) {
   out_8753495689455606364[0] = delta_x[0] + nom_x[0];
   out_8753495689455606364[1] = delta_x[1] + nom_x[1];
   out_8753495689455606364[2] = delta_x[2] + nom_x[2];
   out_8753495689455606364[3] = delta_x[3] + nom_x[3];
   out_8753495689455606364[4] = delta_x[4] + nom_x[4];
   out_8753495689455606364[5] = delta_x[5] + nom_x[5];
   out_8753495689455606364[6] = delta_x[6] + nom_x[6];
   out_8753495689455606364[7] = delta_x[7] + nom_x[7];
   out_8753495689455606364[8] = delta_x[8] + nom_x[8];
   out_8753495689455606364[9] = delta_x[9] + nom_x[9];
   out_8753495689455606364[10] = delta_x[10] + nom_x[10];
   out_8753495689455606364[11] = delta_x[11] + nom_x[11];
   out_8753495689455606364[12] = delta_x[12] + nom_x[12];
   out_8753495689455606364[13] = delta_x[13] + nom_x[13];
   out_8753495689455606364[14] = delta_x[14] + nom_x[14];
   out_8753495689455606364[15] = delta_x[15] + nom_x[15];
   out_8753495689455606364[16] = delta_x[16] + nom_x[16];
   out_8753495689455606364[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7040060865599254852) {
   out_7040060865599254852[0] = -nom_x[0] + true_x[0];
   out_7040060865599254852[1] = -nom_x[1] + true_x[1];
   out_7040060865599254852[2] = -nom_x[2] + true_x[2];
   out_7040060865599254852[3] = -nom_x[3] + true_x[3];
   out_7040060865599254852[4] = -nom_x[4] + true_x[4];
   out_7040060865599254852[5] = -nom_x[5] + true_x[5];
   out_7040060865599254852[6] = -nom_x[6] + true_x[6];
   out_7040060865599254852[7] = -nom_x[7] + true_x[7];
   out_7040060865599254852[8] = -nom_x[8] + true_x[8];
   out_7040060865599254852[9] = -nom_x[9] + true_x[9];
   out_7040060865599254852[10] = -nom_x[10] + true_x[10];
   out_7040060865599254852[11] = -nom_x[11] + true_x[11];
   out_7040060865599254852[12] = -nom_x[12] + true_x[12];
   out_7040060865599254852[13] = -nom_x[13] + true_x[13];
   out_7040060865599254852[14] = -nom_x[14] + true_x[14];
   out_7040060865599254852[15] = -nom_x[15] + true_x[15];
   out_7040060865599254852[16] = -nom_x[16] + true_x[16];
   out_7040060865599254852[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2703870827941122868) {
   out_2703870827941122868[0] = 1.0;
   out_2703870827941122868[1] = 0.0;
   out_2703870827941122868[2] = 0.0;
   out_2703870827941122868[3] = 0.0;
   out_2703870827941122868[4] = 0.0;
   out_2703870827941122868[5] = 0.0;
   out_2703870827941122868[6] = 0.0;
   out_2703870827941122868[7] = 0.0;
   out_2703870827941122868[8] = 0.0;
   out_2703870827941122868[9] = 0.0;
   out_2703870827941122868[10] = 0.0;
   out_2703870827941122868[11] = 0.0;
   out_2703870827941122868[12] = 0.0;
   out_2703870827941122868[13] = 0.0;
   out_2703870827941122868[14] = 0.0;
   out_2703870827941122868[15] = 0.0;
   out_2703870827941122868[16] = 0.0;
   out_2703870827941122868[17] = 0.0;
   out_2703870827941122868[18] = 0.0;
   out_2703870827941122868[19] = 1.0;
   out_2703870827941122868[20] = 0.0;
   out_2703870827941122868[21] = 0.0;
   out_2703870827941122868[22] = 0.0;
   out_2703870827941122868[23] = 0.0;
   out_2703870827941122868[24] = 0.0;
   out_2703870827941122868[25] = 0.0;
   out_2703870827941122868[26] = 0.0;
   out_2703870827941122868[27] = 0.0;
   out_2703870827941122868[28] = 0.0;
   out_2703870827941122868[29] = 0.0;
   out_2703870827941122868[30] = 0.0;
   out_2703870827941122868[31] = 0.0;
   out_2703870827941122868[32] = 0.0;
   out_2703870827941122868[33] = 0.0;
   out_2703870827941122868[34] = 0.0;
   out_2703870827941122868[35] = 0.0;
   out_2703870827941122868[36] = 0.0;
   out_2703870827941122868[37] = 0.0;
   out_2703870827941122868[38] = 1.0;
   out_2703870827941122868[39] = 0.0;
   out_2703870827941122868[40] = 0.0;
   out_2703870827941122868[41] = 0.0;
   out_2703870827941122868[42] = 0.0;
   out_2703870827941122868[43] = 0.0;
   out_2703870827941122868[44] = 0.0;
   out_2703870827941122868[45] = 0.0;
   out_2703870827941122868[46] = 0.0;
   out_2703870827941122868[47] = 0.0;
   out_2703870827941122868[48] = 0.0;
   out_2703870827941122868[49] = 0.0;
   out_2703870827941122868[50] = 0.0;
   out_2703870827941122868[51] = 0.0;
   out_2703870827941122868[52] = 0.0;
   out_2703870827941122868[53] = 0.0;
   out_2703870827941122868[54] = 0.0;
   out_2703870827941122868[55] = 0.0;
   out_2703870827941122868[56] = 0.0;
   out_2703870827941122868[57] = 1.0;
   out_2703870827941122868[58] = 0.0;
   out_2703870827941122868[59] = 0.0;
   out_2703870827941122868[60] = 0.0;
   out_2703870827941122868[61] = 0.0;
   out_2703870827941122868[62] = 0.0;
   out_2703870827941122868[63] = 0.0;
   out_2703870827941122868[64] = 0.0;
   out_2703870827941122868[65] = 0.0;
   out_2703870827941122868[66] = 0.0;
   out_2703870827941122868[67] = 0.0;
   out_2703870827941122868[68] = 0.0;
   out_2703870827941122868[69] = 0.0;
   out_2703870827941122868[70] = 0.0;
   out_2703870827941122868[71] = 0.0;
   out_2703870827941122868[72] = 0.0;
   out_2703870827941122868[73] = 0.0;
   out_2703870827941122868[74] = 0.0;
   out_2703870827941122868[75] = 0.0;
   out_2703870827941122868[76] = 1.0;
   out_2703870827941122868[77] = 0.0;
   out_2703870827941122868[78] = 0.0;
   out_2703870827941122868[79] = 0.0;
   out_2703870827941122868[80] = 0.0;
   out_2703870827941122868[81] = 0.0;
   out_2703870827941122868[82] = 0.0;
   out_2703870827941122868[83] = 0.0;
   out_2703870827941122868[84] = 0.0;
   out_2703870827941122868[85] = 0.0;
   out_2703870827941122868[86] = 0.0;
   out_2703870827941122868[87] = 0.0;
   out_2703870827941122868[88] = 0.0;
   out_2703870827941122868[89] = 0.0;
   out_2703870827941122868[90] = 0.0;
   out_2703870827941122868[91] = 0.0;
   out_2703870827941122868[92] = 0.0;
   out_2703870827941122868[93] = 0.0;
   out_2703870827941122868[94] = 0.0;
   out_2703870827941122868[95] = 1.0;
   out_2703870827941122868[96] = 0.0;
   out_2703870827941122868[97] = 0.0;
   out_2703870827941122868[98] = 0.0;
   out_2703870827941122868[99] = 0.0;
   out_2703870827941122868[100] = 0.0;
   out_2703870827941122868[101] = 0.0;
   out_2703870827941122868[102] = 0.0;
   out_2703870827941122868[103] = 0.0;
   out_2703870827941122868[104] = 0.0;
   out_2703870827941122868[105] = 0.0;
   out_2703870827941122868[106] = 0.0;
   out_2703870827941122868[107] = 0.0;
   out_2703870827941122868[108] = 0.0;
   out_2703870827941122868[109] = 0.0;
   out_2703870827941122868[110] = 0.0;
   out_2703870827941122868[111] = 0.0;
   out_2703870827941122868[112] = 0.0;
   out_2703870827941122868[113] = 0.0;
   out_2703870827941122868[114] = 1.0;
   out_2703870827941122868[115] = 0.0;
   out_2703870827941122868[116] = 0.0;
   out_2703870827941122868[117] = 0.0;
   out_2703870827941122868[118] = 0.0;
   out_2703870827941122868[119] = 0.0;
   out_2703870827941122868[120] = 0.0;
   out_2703870827941122868[121] = 0.0;
   out_2703870827941122868[122] = 0.0;
   out_2703870827941122868[123] = 0.0;
   out_2703870827941122868[124] = 0.0;
   out_2703870827941122868[125] = 0.0;
   out_2703870827941122868[126] = 0.0;
   out_2703870827941122868[127] = 0.0;
   out_2703870827941122868[128] = 0.0;
   out_2703870827941122868[129] = 0.0;
   out_2703870827941122868[130] = 0.0;
   out_2703870827941122868[131] = 0.0;
   out_2703870827941122868[132] = 0.0;
   out_2703870827941122868[133] = 1.0;
   out_2703870827941122868[134] = 0.0;
   out_2703870827941122868[135] = 0.0;
   out_2703870827941122868[136] = 0.0;
   out_2703870827941122868[137] = 0.0;
   out_2703870827941122868[138] = 0.0;
   out_2703870827941122868[139] = 0.0;
   out_2703870827941122868[140] = 0.0;
   out_2703870827941122868[141] = 0.0;
   out_2703870827941122868[142] = 0.0;
   out_2703870827941122868[143] = 0.0;
   out_2703870827941122868[144] = 0.0;
   out_2703870827941122868[145] = 0.0;
   out_2703870827941122868[146] = 0.0;
   out_2703870827941122868[147] = 0.0;
   out_2703870827941122868[148] = 0.0;
   out_2703870827941122868[149] = 0.0;
   out_2703870827941122868[150] = 0.0;
   out_2703870827941122868[151] = 0.0;
   out_2703870827941122868[152] = 1.0;
   out_2703870827941122868[153] = 0.0;
   out_2703870827941122868[154] = 0.0;
   out_2703870827941122868[155] = 0.0;
   out_2703870827941122868[156] = 0.0;
   out_2703870827941122868[157] = 0.0;
   out_2703870827941122868[158] = 0.0;
   out_2703870827941122868[159] = 0.0;
   out_2703870827941122868[160] = 0.0;
   out_2703870827941122868[161] = 0.0;
   out_2703870827941122868[162] = 0.0;
   out_2703870827941122868[163] = 0.0;
   out_2703870827941122868[164] = 0.0;
   out_2703870827941122868[165] = 0.0;
   out_2703870827941122868[166] = 0.0;
   out_2703870827941122868[167] = 0.0;
   out_2703870827941122868[168] = 0.0;
   out_2703870827941122868[169] = 0.0;
   out_2703870827941122868[170] = 0.0;
   out_2703870827941122868[171] = 1.0;
   out_2703870827941122868[172] = 0.0;
   out_2703870827941122868[173] = 0.0;
   out_2703870827941122868[174] = 0.0;
   out_2703870827941122868[175] = 0.0;
   out_2703870827941122868[176] = 0.0;
   out_2703870827941122868[177] = 0.0;
   out_2703870827941122868[178] = 0.0;
   out_2703870827941122868[179] = 0.0;
   out_2703870827941122868[180] = 0.0;
   out_2703870827941122868[181] = 0.0;
   out_2703870827941122868[182] = 0.0;
   out_2703870827941122868[183] = 0.0;
   out_2703870827941122868[184] = 0.0;
   out_2703870827941122868[185] = 0.0;
   out_2703870827941122868[186] = 0.0;
   out_2703870827941122868[187] = 0.0;
   out_2703870827941122868[188] = 0.0;
   out_2703870827941122868[189] = 0.0;
   out_2703870827941122868[190] = 1.0;
   out_2703870827941122868[191] = 0.0;
   out_2703870827941122868[192] = 0.0;
   out_2703870827941122868[193] = 0.0;
   out_2703870827941122868[194] = 0.0;
   out_2703870827941122868[195] = 0.0;
   out_2703870827941122868[196] = 0.0;
   out_2703870827941122868[197] = 0.0;
   out_2703870827941122868[198] = 0.0;
   out_2703870827941122868[199] = 0.0;
   out_2703870827941122868[200] = 0.0;
   out_2703870827941122868[201] = 0.0;
   out_2703870827941122868[202] = 0.0;
   out_2703870827941122868[203] = 0.0;
   out_2703870827941122868[204] = 0.0;
   out_2703870827941122868[205] = 0.0;
   out_2703870827941122868[206] = 0.0;
   out_2703870827941122868[207] = 0.0;
   out_2703870827941122868[208] = 0.0;
   out_2703870827941122868[209] = 1.0;
   out_2703870827941122868[210] = 0.0;
   out_2703870827941122868[211] = 0.0;
   out_2703870827941122868[212] = 0.0;
   out_2703870827941122868[213] = 0.0;
   out_2703870827941122868[214] = 0.0;
   out_2703870827941122868[215] = 0.0;
   out_2703870827941122868[216] = 0.0;
   out_2703870827941122868[217] = 0.0;
   out_2703870827941122868[218] = 0.0;
   out_2703870827941122868[219] = 0.0;
   out_2703870827941122868[220] = 0.0;
   out_2703870827941122868[221] = 0.0;
   out_2703870827941122868[222] = 0.0;
   out_2703870827941122868[223] = 0.0;
   out_2703870827941122868[224] = 0.0;
   out_2703870827941122868[225] = 0.0;
   out_2703870827941122868[226] = 0.0;
   out_2703870827941122868[227] = 0.0;
   out_2703870827941122868[228] = 1.0;
   out_2703870827941122868[229] = 0.0;
   out_2703870827941122868[230] = 0.0;
   out_2703870827941122868[231] = 0.0;
   out_2703870827941122868[232] = 0.0;
   out_2703870827941122868[233] = 0.0;
   out_2703870827941122868[234] = 0.0;
   out_2703870827941122868[235] = 0.0;
   out_2703870827941122868[236] = 0.0;
   out_2703870827941122868[237] = 0.0;
   out_2703870827941122868[238] = 0.0;
   out_2703870827941122868[239] = 0.0;
   out_2703870827941122868[240] = 0.0;
   out_2703870827941122868[241] = 0.0;
   out_2703870827941122868[242] = 0.0;
   out_2703870827941122868[243] = 0.0;
   out_2703870827941122868[244] = 0.0;
   out_2703870827941122868[245] = 0.0;
   out_2703870827941122868[246] = 0.0;
   out_2703870827941122868[247] = 1.0;
   out_2703870827941122868[248] = 0.0;
   out_2703870827941122868[249] = 0.0;
   out_2703870827941122868[250] = 0.0;
   out_2703870827941122868[251] = 0.0;
   out_2703870827941122868[252] = 0.0;
   out_2703870827941122868[253] = 0.0;
   out_2703870827941122868[254] = 0.0;
   out_2703870827941122868[255] = 0.0;
   out_2703870827941122868[256] = 0.0;
   out_2703870827941122868[257] = 0.0;
   out_2703870827941122868[258] = 0.0;
   out_2703870827941122868[259] = 0.0;
   out_2703870827941122868[260] = 0.0;
   out_2703870827941122868[261] = 0.0;
   out_2703870827941122868[262] = 0.0;
   out_2703870827941122868[263] = 0.0;
   out_2703870827941122868[264] = 0.0;
   out_2703870827941122868[265] = 0.0;
   out_2703870827941122868[266] = 1.0;
   out_2703870827941122868[267] = 0.0;
   out_2703870827941122868[268] = 0.0;
   out_2703870827941122868[269] = 0.0;
   out_2703870827941122868[270] = 0.0;
   out_2703870827941122868[271] = 0.0;
   out_2703870827941122868[272] = 0.0;
   out_2703870827941122868[273] = 0.0;
   out_2703870827941122868[274] = 0.0;
   out_2703870827941122868[275] = 0.0;
   out_2703870827941122868[276] = 0.0;
   out_2703870827941122868[277] = 0.0;
   out_2703870827941122868[278] = 0.0;
   out_2703870827941122868[279] = 0.0;
   out_2703870827941122868[280] = 0.0;
   out_2703870827941122868[281] = 0.0;
   out_2703870827941122868[282] = 0.0;
   out_2703870827941122868[283] = 0.0;
   out_2703870827941122868[284] = 0.0;
   out_2703870827941122868[285] = 1.0;
   out_2703870827941122868[286] = 0.0;
   out_2703870827941122868[287] = 0.0;
   out_2703870827941122868[288] = 0.0;
   out_2703870827941122868[289] = 0.0;
   out_2703870827941122868[290] = 0.0;
   out_2703870827941122868[291] = 0.0;
   out_2703870827941122868[292] = 0.0;
   out_2703870827941122868[293] = 0.0;
   out_2703870827941122868[294] = 0.0;
   out_2703870827941122868[295] = 0.0;
   out_2703870827941122868[296] = 0.0;
   out_2703870827941122868[297] = 0.0;
   out_2703870827941122868[298] = 0.0;
   out_2703870827941122868[299] = 0.0;
   out_2703870827941122868[300] = 0.0;
   out_2703870827941122868[301] = 0.0;
   out_2703870827941122868[302] = 0.0;
   out_2703870827941122868[303] = 0.0;
   out_2703870827941122868[304] = 1.0;
   out_2703870827941122868[305] = 0.0;
   out_2703870827941122868[306] = 0.0;
   out_2703870827941122868[307] = 0.0;
   out_2703870827941122868[308] = 0.0;
   out_2703870827941122868[309] = 0.0;
   out_2703870827941122868[310] = 0.0;
   out_2703870827941122868[311] = 0.0;
   out_2703870827941122868[312] = 0.0;
   out_2703870827941122868[313] = 0.0;
   out_2703870827941122868[314] = 0.0;
   out_2703870827941122868[315] = 0.0;
   out_2703870827941122868[316] = 0.0;
   out_2703870827941122868[317] = 0.0;
   out_2703870827941122868[318] = 0.0;
   out_2703870827941122868[319] = 0.0;
   out_2703870827941122868[320] = 0.0;
   out_2703870827941122868[321] = 0.0;
   out_2703870827941122868[322] = 0.0;
   out_2703870827941122868[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8883447168535687566) {
   out_8883447168535687566[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8883447168535687566[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8883447168535687566[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8883447168535687566[3] = dt*state[12] + state[3];
   out_8883447168535687566[4] = dt*state[13] + state[4];
   out_8883447168535687566[5] = dt*state[14] + state[5];
   out_8883447168535687566[6] = state[6];
   out_8883447168535687566[7] = state[7];
   out_8883447168535687566[8] = state[8];
   out_8883447168535687566[9] = state[9];
   out_8883447168535687566[10] = state[10];
   out_8883447168535687566[11] = state[11];
   out_8883447168535687566[12] = state[12];
   out_8883447168535687566[13] = state[13];
   out_8883447168535687566[14] = state[14];
   out_8883447168535687566[15] = state[15];
   out_8883447168535687566[16] = state[16];
   out_8883447168535687566[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5352116671186116134) {
   out_5352116671186116134[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5352116671186116134[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5352116671186116134[2] = 0;
   out_5352116671186116134[3] = 0;
   out_5352116671186116134[4] = 0;
   out_5352116671186116134[5] = 0;
   out_5352116671186116134[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5352116671186116134[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5352116671186116134[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5352116671186116134[9] = 0;
   out_5352116671186116134[10] = 0;
   out_5352116671186116134[11] = 0;
   out_5352116671186116134[12] = 0;
   out_5352116671186116134[13] = 0;
   out_5352116671186116134[14] = 0;
   out_5352116671186116134[15] = 0;
   out_5352116671186116134[16] = 0;
   out_5352116671186116134[17] = 0;
   out_5352116671186116134[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5352116671186116134[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5352116671186116134[20] = 0;
   out_5352116671186116134[21] = 0;
   out_5352116671186116134[22] = 0;
   out_5352116671186116134[23] = 0;
   out_5352116671186116134[24] = 0;
   out_5352116671186116134[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5352116671186116134[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5352116671186116134[27] = 0;
   out_5352116671186116134[28] = 0;
   out_5352116671186116134[29] = 0;
   out_5352116671186116134[30] = 0;
   out_5352116671186116134[31] = 0;
   out_5352116671186116134[32] = 0;
   out_5352116671186116134[33] = 0;
   out_5352116671186116134[34] = 0;
   out_5352116671186116134[35] = 0;
   out_5352116671186116134[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5352116671186116134[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5352116671186116134[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5352116671186116134[39] = 0;
   out_5352116671186116134[40] = 0;
   out_5352116671186116134[41] = 0;
   out_5352116671186116134[42] = 0;
   out_5352116671186116134[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5352116671186116134[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5352116671186116134[45] = 0;
   out_5352116671186116134[46] = 0;
   out_5352116671186116134[47] = 0;
   out_5352116671186116134[48] = 0;
   out_5352116671186116134[49] = 0;
   out_5352116671186116134[50] = 0;
   out_5352116671186116134[51] = 0;
   out_5352116671186116134[52] = 0;
   out_5352116671186116134[53] = 0;
   out_5352116671186116134[54] = 0;
   out_5352116671186116134[55] = 0;
   out_5352116671186116134[56] = 0;
   out_5352116671186116134[57] = 1;
   out_5352116671186116134[58] = 0;
   out_5352116671186116134[59] = 0;
   out_5352116671186116134[60] = 0;
   out_5352116671186116134[61] = 0;
   out_5352116671186116134[62] = 0;
   out_5352116671186116134[63] = 0;
   out_5352116671186116134[64] = 0;
   out_5352116671186116134[65] = 0;
   out_5352116671186116134[66] = dt;
   out_5352116671186116134[67] = 0;
   out_5352116671186116134[68] = 0;
   out_5352116671186116134[69] = 0;
   out_5352116671186116134[70] = 0;
   out_5352116671186116134[71] = 0;
   out_5352116671186116134[72] = 0;
   out_5352116671186116134[73] = 0;
   out_5352116671186116134[74] = 0;
   out_5352116671186116134[75] = 0;
   out_5352116671186116134[76] = 1;
   out_5352116671186116134[77] = 0;
   out_5352116671186116134[78] = 0;
   out_5352116671186116134[79] = 0;
   out_5352116671186116134[80] = 0;
   out_5352116671186116134[81] = 0;
   out_5352116671186116134[82] = 0;
   out_5352116671186116134[83] = 0;
   out_5352116671186116134[84] = 0;
   out_5352116671186116134[85] = dt;
   out_5352116671186116134[86] = 0;
   out_5352116671186116134[87] = 0;
   out_5352116671186116134[88] = 0;
   out_5352116671186116134[89] = 0;
   out_5352116671186116134[90] = 0;
   out_5352116671186116134[91] = 0;
   out_5352116671186116134[92] = 0;
   out_5352116671186116134[93] = 0;
   out_5352116671186116134[94] = 0;
   out_5352116671186116134[95] = 1;
   out_5352116671186116134[96] = 0;
   out_5352116671186116134[97] = 0;
   out_5352116671186116134[98] = 0;
   out_5352116671186116134[99] = 0;
   out_5352116671186116134[100] = 0;
   out_5352116671186116134[101] = 0;
   out_5352116671186116134[102] = 0;
   out_5352116671186116134[103] = 0;
   out_5352116671186116134[104] = dt;
   out_5352116671186116134[105] = 0;
   out_5352116671186116134[106] = 0;
   out_5352116671186116134[107] = 0;
   out_5352116671186116134[108] = 0;
   out_5352116671186116134[109] = 0;
   out_5352116671186116134[110] = 0;
   out_5352116671186116134[111] = 0;
   out_5352116671186116134[112] = 0;
   out_5352116671186116134[113] = 0;
   out_5352116671186116134[114] = 1;
   out_5352116671186116134[115] = 0;
   out_5352116671186116134[116] = 0;
   out_5352116671186116134[117] = 0;
   out_5352116671186116134[118] = 0;
   out_5352116671186116134[119] = 0;
   out_5352116671186116134[120] = 0;
   out_5352116671186116134[121] = 0;
   out_5352116671186116134[122] = 0;
   out_5352116671186116134[123] = 0;
   out_5352116671186116134[124] = 0;
   out_5352116671186116134[125] = 0;
   out_5352116671186116134[126] = 0;
   out_5352116671186116134[127] = 0;
   out_5352116671186116134[128] = 0;
   out_5352116671186116134[129] = 0;
   out_5352116671186116134[130] = 0;
   out_5352116671186116134[131] = 0;
   out_5352116671186116134[132] = 0;
   out_5352116671186116134[133] = 1;
   out_5352116671186116134[134] = 0;
   out_5352116671186116134[135] = 0;
   out_5352116671186116134[136] = 0;
   out_5352116671186116134[137] = 0;
   out_5352116671186116134[138] = 0;
   out_5352116671186116134[139] = 0;
   out_5352116671186116134[140] = 0;
   out_5352116671186116134[141] = 0;
   out_5352116671186116134[142] = 0;
   out_5352116671186116134[143] = 0;
   out_5352116671186116134[144] = 0;
   out_5352116671186116134[145] = 0;
   out_5352116671186116134[146] = 0;
   out_5352116671186116134[147] = 0;
   out_5352116671186116134[148] = 0;
   out_5352116671186116134[149] = 0;
   out_5352116671186116134[150] = 0;
   out_5352116671186116134[151] = 0;
   out_5352116671186116134[152] = 1;
   out_5352116671186116134[153] = 0;
   out_5352116671186116134[154] = 0;
   out_5352116671186116134[155] = 0;
   out_5352116671186116134[156] = 0;
   out_5352116671186116134[157] = 0;
   out_5352116671186116134[158] = 0;
   out_5352116671186116134[159] = 0;
   out_5352116671186116134[160] = 0;
   out_5352116671186116134[161] = 0;
   out_5352116671186116134[162] = 0;
   out_5352116671186116134[163] = 0;
   out_5352116671186116134[164] = 0;
   out_5352116671186116134[165] = 0;
   out_5352116671186116134[166] = 0;
   out_5352116671186116134[167] = 0;
   out_5352116671186116134[168] = 0;
   out_5352116671186116134[169] = 0;
   out_5352116671186116134[170] = 0;
   out_5352116671186116134[171] = 1;
   out_5352116671186116134[172] = 0;
   out_5352116671186116134[173] = 0;
   out_5352116671186116134[174] = 0;
   out_5352116671186116134[175] = 0;
   out_5352116671186116134[176] = 0;
   out_5352116671186116134[177] = 0;
   out_5352116671186116134[178] = 0;
   out_5352116671186116134[179] = 0;
   out_5352116671186116134[180] = 0;
   out_5352116671186116134[181] = 0;
   out_5352116671186116134[182] = 0;
   out_5352116671186116134[183] = 0;
   out_5352116671186116134[184] = 0;
   out_5352116671186116134[185] = 0;
   out_5352116671186116134[186] = 0;
   out_5352116671186116134[187] = 0;
   out_5352116671186116134[188] = 0;
   out_5352116671186116134[189] = 0;
   out_5352116671186116134[190] = 1;
   out_5352116671186116134[191] = 0;
   out_5352116671186116134[192] = 0;
   out_5352116671186116134[193] = 0;
   out_5352116671186116134[194] = 0;
   out_5352116671186116134[195] = 0;
   out_5352116671186116134[196] = 0;
   out_5352116671186116134[197] = 0;
   out_5352116671186116134[198] = 0;
   out_5352116671186116134[199] = 0;
   out_5352116671186116134[200] = 0;
   out_5352116671186116134[201] = 0;
   out_5352116671186116134[202] = 0;
   out_5352116671186116134[203] = 0;
   out_5352116671186116134[204] = 0;
   out_5352116671186116134[205] = 0;
   out_5352116671186116134[206] = 0;
   out_5352116671186116134[207] = 0;
   out_5352116671186116134[208] = 0;
   out_5352116671186116134[209] = 1;
   out_5352116671186116134[210] = 0;
   out_5352116671186116134[211] = 0;
   out_5352116671186116134[212] = 0;
   out_5352116671186116134[213] = 0;
   out_5352116671186116134[214] = 0;
   out_5352116671186116134[215] = 0;
   out_5352116671186116134[216] = 0;
   out_5352116671186116134[217] = 0;
   out_5352116671186116134[218] = 0;
   out_5352116671186116134[219] = 0;
   out_5352116671186116134[220] = 0;
   out_5352116671186116134[221] = 0;
   out_5352116671186116134[222] = 0;
   out_5352116671186116134[223] = 0;
   out_5352116671186116134[224] = 0;
   out_5352116671186116134[225] = 0;
   out_5352116671186116134[226] = 0;
   out_5352116671186116134[227] = 0;
   out_5352116671186116134[228] = 1;
   out_5352116671186116134[229] = 0;
   out_5352116671186116134[230] = 0;
   out_5352116671186116134[231] = 0;
   out_5352116671186116134[232] = 0;
   out_5352116671186116134[233] = 0;
   out_5352116671186116134[234] = 0;
   out_5352116671186116134[235] = 0;
   out_5352116671186116134[236] = 0;
   out_5352116671186116134[237] = 0;
   out_5352116671186116134[238] = 0;
   out_5352116671186116134[239] = 0;
   out_5352116671186116134[240] = 0;
   out_5352116671186116134[241] = 0;
   out_5352116671186116134[242] = 0;
   out_5352116671186116134[243] = 0;
   out_5352116671186116134[244] = 0;
   out_5352116671186116134[245] = 0;
   out_5352116671186116134[246] = 0;
   out_5352116671186116134[247] = 1;
   out_5352116671186116134[248] = 0;
   out_5352116671186116134[249] = 0;
   out_5352116671186116134[250] = 0;
   out_5352116671186116134[251] = 0;
   out_5352116671186116134[252] = 0;
   out_5352116671186116134[253] = 0;
   out_5352116671186116134[254] = 0;
   out_5352116671186116134[255] = 0;
   out_5352116671186116134[256] = 0;
   out_5352116671186116134[257] = 0;
   out_5352116671186116134[258] = 0;
   out_5352116671186116134[259] = 0;
   out_5352116671186116134[260] = 0;
   out_5352116671186116134[261] = 0;
   out_5352116671186116134[262] = 0;
   out_5352116671186116134[263] = 0;
   out_5352116671186116134[264] = 0;
   out_5352116671186116134[265] = 0;
   out_5352116671186116134[266] = 1;
   out_5352116671186116134[267] = 0;
   out_5352116671186116134[268] = 0;
   out_5352116671186116134[269] = 0;
   out_5352116671186116134[270] = 0;
   out_5352116671186116134[271] = 0;
   out_5352116671186116134[272] = 0;
   out_5352116671186116134[273] = 0;
   out_5352116671186116134[274] = 0;
   out_5352116671186116134[275] = 0;
   out_5352116671186116134[276] = 0;
   out_5352116671186116134[277] = 0;
   out_5352116671186116134[278] = 0;
   out_5352116671186116134[279] = 0;
   out_5352116671186116134[280] = 0;
   out_5352116671186116134[281] = 0;
   out_5352116671186116134[282] = 0;
   out_5352116671186116134[283] = 0;
   out_5352116671186116134[284] = 0;
   out_5352116671186116134[285] = 1;
   out_5352116671186116134[286] = 0;
   out_5352116671186116134[287] = 0;
   out_5352116671186116134[288] = 0;
   out_5352116671186116134[289] = 0;
   out_5352116671186116134[290] = 0;
   out_5352116671186116134[291] = 0;
   out_5352116671186116134[292] = 0;
   out_5352116671186116134[293] = 0;
   out_5352116671186116134[294] = 0;
   out_5352116671186116134[295] = 0;
   out_5352116671186116134[296] = 0;
   out_5352116671186116134[297] = 0;
   out_5352116671186116134[298] = 0;
   out_5352116671186116134[299] = 0;
   out_5352116671186116134[300] = 0;
   out_5352116671186116134[301] = 0;
   out_5352116671186116134[302] = 0;
   out_5352116671186116134[303] = 0;
   out_5352116671186116134[304] = 1;
   out_5352116671186116134[305] = 0;
   out_5352116671186116134[306] = 0;
   out_5352116671186116134[307] = 0;
   out_5352116671186116134[308] = 0;
   out_5352116671186116134[309] = 0;
   out_5352116671186116134[310] = 0;
   out_5352116671186116134[311] = 0;
   out_5352116671186116134[312] = 0;
   out_5352116671186116134[313] = 0;
   out_5352116671186116134[314] = 0;
   out_5352116671186116134[315] = 0;
   out_5352116671186116134[316] = 0;
   out_5352116671186116134[317] = 0;
   out_5352116671186116134[318] = 0;
   out_5352116671186116134[319] = 0;
   out_5352116671186116134[320] = 0;
   out_5352116671186116134[321] = 0;
   out_5352116671186116134[322] = 0;
   out_5352116671186116134[323] = 1;
}
void h_4(double *state, double *unused, double *out_7227081021545178632) {
   out_7227081021545178632[0] = state[6] + state[9];
   out_7227081021545178632[1] = state[7] + state[10];
   out_7227081021545178632[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_496539073160347156) {
   out_496539073160347156[0] = 0;
   out_496539073160347156[1] = 0;
   out_496539073160347156[2] = 0;
   out_496539073160347156[3] = 0;
   out_496539073160347156[4] = 0;
   out_496539073160347156[5] = 0;
   out_496539073160347156[6] = 1;
   out_496539073160347156[7] = 0;
   out_496539073160347156[8] = 0;
   out_496539073160347156[9] = 1;
   out_496539073160347156[10] = 0;
   out_496539073160347156[11] = 0;
   out_496539073160347156[12] = 0;
   out_496539073160347156[13] = 0;
   out_496539073160347156[14] = 0;
   out_496539073160347156[15] = 0;
   out_496539073160347156[16] = 0;
   out_496539073160347156[17] = 0;
   out_496539073160347156[18] = 0;
   out_496539073160347156[19] = 0;
   out_496539073160347156[20] = 0;
   out_496539073160347156[21] = 0;
   out_496539073160347156[22] = 0;
   out_496539073160347156[23] = 0;
   out_496539073160347156[24] = 0;
   out_496539073160347156[25] = 1;
   out_496539073160347156[26] = 0;
   out_496539073160347156[27] = 0;
   out_496539073160347156[28] = 1;
   out_496539073160347156[29] = 0;
   out_496539073160347156[30] = 0;
   out_496539073160347156[31] = 0;
   out_496539073160347156[32] = 0;
   out_496539073160347156[33] = 0;
   out_496539073160347156[34] = 0;
   out_496539073160347156[35] = 0;
   out_496539073160347156[36] = 0;
   out_496539073160347156[37] = 0;
   out_496539073160347156[38] = 0;
   out_496539073160347156[39] = 0;
   out_496539073160347156[40] = 0;
   out_496539073160347156[41] = 0;
   out_496539073160347156[42] = 0;
   out_496539073160347156[43] = 0;
   out_496539073160347156[44] = 1;
   out_496539073160347156[45] = 0;
   out_496539073160347156[46] = 0;
   out_496539073160347156[47] = 1;
   out_496539073160347156[48] = 0;
   out_496539073160347156[49] = 0;
   out_496539073160347156[50] = 0;
   out_496539073160347156[51] = 0;
   out_496539073160347156[52] = 0;
   out_496539073160347156[53] = 0;
}
void h_10(double *state, double *unused, double *out_1880125658668972037) {
   out_1880125658668972037[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1880125658668972037[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1880125658668972037[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6033877093640339494) {
   out_6033877093640339494[0] = 0;
   out_6033877093640339494[1] = 9.8100000000000005*cos(state[1]);
   out_6033877093640339494[2] = 0;
   out_6033877093640339494[3] = 0;
   out_6033877093640339494[4] = -state[8];
   out_6033877093640339494[5] = state[7];
   out_6033877093640339494[6] = 0;
   out_6033877093640339494[7] = state[5];
   out_6033877093640339494[8] = -state[4];
   out_6033877093640339494[9] = 0;
   out_6033877093640339494[10] = 0;
   out_6033877093640339494[11] = 0;
   out_6033877093640339494[12] = 1;
   out_6033877093640339494[13] = 0;
   out_6033877093640339494[14] = 0;
   out_6033877093640339494[15] = 1;
   out_6033877093640339494[16] = 0;
   out_6033877093640339494[17] = 0;
   out_6033877093640339494[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6033877093640339494[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6033877093640339494[20] = 0;
   out_6033877093640339494[21] = state[8];
   out_6033877093640339494[22] = 0;
   out_6033877093640339494[23] = -state[6];
   out_6033877093640339494[24] = -state[5];
   out_6033877093640339494[25] = 0;
   out_6033877093640339494[26] = state[3];
   out_6033877093640339494[27] = 0;
   out_6033877093640339494[28] = 0;
   out_6033877093640339494[29] = 0;
   out_6033877093640339494[30] = 0;
   out_6033877093640339494[31] = 1;
   out_6033877093640339494[32] = 0;
   out_6033877093640339494[33] = 0;
   out_6033877093640339494[34] = 1;
   out_6033877093640339494[35] = 0;
   out_6033877093640339494[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6033877093640339494[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6033877093640339494[38] = 0;
   out_6033877093640339494[39] = -state[7];
   out_6033877093640339494[40] = state[6];
   out_6033877093640339494[41] = 0;
   out_6033877093640339494[42] = state[4];
   out_6033877093640339494[43] = -state[3];
   out_6033877093640339494[44] = 0;
   out_6033877093640339494[45] = 0;
   out_6033877093640339494[46] = 0;
   out_6033877093640339494[47] = 0;
   out_6033877093640339494[48] = 0;
   out_6033877093640339494[49] = 0;
   out_6033877093640339494[50] = 1;
   out_6033877093640339494[51] = 0;
   out_6033877093640339494[52] = 0;
   out_6033877093640339494[53] = 1;
}
void h_13(double *state, double *unused, double *out_7805785120847628893) {
   out_7805785120847628893[0] = state[3];
   out_7805785120847628893[1] = state[4];
   out_7805785120847628893[2] = state[5];
}
void H_13(double *state, double *unused, double *out_68062846521496948) {
   out_68062846521496948[0] = 0;
   out_68062846521496948[1] = 0;
   out_68062846521496948[2] = 0;
   out_68062846521496948[3] = 1;
   out_68062846521496948[4] = 0;
   out_68062846521496948[5] = 0;
   out_68062846521496948[6] = 0;
   out_68062846521496948[7] = 0;
   out_68062846521496948[8] = 0;
   out_68062846521496948[9] = 0;
   out_68062846521496948[10] = 0;
   out_68062846521496948[11] = 0;
   out_68062846521496948[12] = 0;
   out_68062846521496948[13] = 0;
   out_68062846521496948[14] = 0;
   out_68062846521496948[15] = 0;
   out_68062846521496948[16] = 0;
   out_68062846521496948[17] = 0;
   out_68062846521496948[18] = 0;
   out_68062846521496948[19] = 0;
   out_68062846521496948[20] = 0;
   out_68062846521496948[21] = 0;
   out_68062846521496948[22] = 1;
   out_68062846521496948[23] = 0;
   out_68062846521496948[24] = 0;
   out_68062846521496948[25] = 0;
   out_68062846521496948[26] = 0;
   out_68062846521496948[27] = 0;
   out_68062846521496948[28] = 0;
   out_68062846521496948[29] = 0;
   out_68062846521496948[30] = 0;
   out_68062846521496948[31] = 0;
   out_68062846521496948[32] = 0;
   out_68062846521496948[33] = 0;
   out_68062846521496948[34] = 0;
   out_68062846521496948[35] = 0;
   out_68062846521496948[36] = 0;
   out_68062846521496948[37] = 0;
   out_68062846521496948[38] = 0;
   out_68062846521496948[39] = 0;
   out_68062846521496948[40] = 0;
   out_68062846521496948[41] = 1;
   out_68062846521496948[42] = 0;
   out_68062846521496948[43] = 0;
   out_68062846521496948[44] = 0;
   out_68062846521496948[45] = 0;
   out_68062846521496948[46] = 0;
   out_68062846521496948[47] = 0;
   out_68062846521496948[48] = 0;
   out_68062846521496948[49] = 0;
   out_68062846521496948[50] = 0;
   out_68062846521496948[51] = 0;
   out_68062846521496948[52] = 0;
   out_68062846521496948[53] = 0;
}
void h_14(double *state, double *unused, double *out_5362476079090588) {
   out_5362476079090588[0] = state[6];
   out_5362476079090588[1] = state[7];
   out_5362476079090588[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3579327505455719452) {
   out_3579327505455719452[0] = 0;
   out_3579327505455719452[1] = 0;
   out_3579327505455719452[2] = 0;
   out_3579327505455719452[3] = 0;
   out_3579327505455719452[4] = 0;
   out_3579327505455719452[5] = 0;
   out_3579327505455719452[6] = 1;
   out_3579327505455719452[7] = 0;
   out_3579327505455719452[8] = 0;
   out_3579327505455719452[9] = 0;
   out_3579327505455719452[10] = 0;
   out_3579327505455719452[11] = 0;
   out_3579327505455719452[12] = 0;
   out_3579327505455719452[13] = 0;
   out_3579327505455719452[14] = 0;
   out_3579327505455719452[15] = 0;
   out_3579327505455719452[16] = 0;
   out_3579327505455719452[17] = 0;
   out_3579327505455719452[18] = 0;
   out_3579327505455719452[19] = 0;
   out_3579327505455719452[20] = 0;
   out_3579327505455719452[21] = 0;
   out_3579327505455719452[22] = 0;
   out_3579327505455719452[23] = 0;
   out_3579327505455719452[24] = 0;
   out_3579327505455719452[25] = 1;
   out_3579327505455719452[26] = 0;
   out_3579327505455719452[27] = 0;
   out_3579327505455719452[28] = 0;
   out_3579327505455719452[29] = 0;
   out_3579327505455719452[30] = 0;
   out_3579327505455719452[31] = 0;
   out_3579327505455719452[32] = 0;
   out_3579327505455719452[33] = 0;
   out_3579327505455719452[34] = 0;
   out_3579327505455719452[35] = 0;
   out_3579327505455719452[36] = 0;
   out_3579327505455719452[37] = 0;
   out_3579327505455719452[38] = 0;
   out_3579327505455719452[39] = 0;
   out_3579327505455719452[40] = 0;
   out_3579327505455719452[41] = 0;
   out_3579327505455719452[42] = 0;
   out_3579327505455719452[43] = 0;
   out_3579327505455719452[44] = 1;
   out_3579327505455719452[45] = 0;
   out_3579327505455719452[46] = 0;
   out_3579327505455719452[47] = 0;
   out_3579327505455719452[48] = 0;
   out_3579327505455719452[49] = 0;
   out_3579327505455719452[50] = 0;
   out_3579327505455719452[51] = 0;
   out_3579327505455719452[52] = 0;
   out_3579327505455719452[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8753495689455606364) {
  err_fun(nom_x, delta_x, out_8753495689455606364);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7040060865599254852) {
  inv_err_fun(nom_x, true_x, out_7040060865599254852);
}
void pose_H_mod_fun(double *state, double *out_2703870827941122868) {
  H_mod_fun(state, out_2703870827941122868);
}
void pose_f_fun(double *state, double dt, double *out_8883447168535687566) {
  f_fun(state,  dt, out_8883447168535687566);
}
void pose_F_fun(double *state, double dt, double *out_5352116671186116134) {
  F_fun(state,  dt, out_5352116671186116134);
}
void pose_h_4(double *state, double *unused, double *out_7227081021545178632) {
  h_4(state, unused, out_7227081021545178632);
}
void pose_H_4(double *state, double *unused, double *out_496539073160347156) {
  H_4(state, unused, out_496539073160347156);
}
void pose_h_10(double *state, double *unused, double *out_1880125658668972037) {
  h_10(state, unused, out_1880125658668972037);
}
void pose_H_10(double *state, double *unused, double *out_6033877093640339494) {
  H_10(state, unused, out_6033877093640339494);
}
void pose_h_13(double *state, double *unused, double *out_7805785120847628893) {
  h_13(state, unused, out_7805785120847628893);
}
void pose_H_13(double *state, double *unused, double *out_68062846521496948) {
  H_13(state, unused, out_68062846521496948);
}
void pose_h_14(double *state, double *unused, double *out_5362476079090588) {
  h_14(state, unused, out_5362476079090588);
}
void pose_H_14(double *state, double *unused, double *out_3579327505455719452) {
  H_14(state, unused, out_3579327505455719452);
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
