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
void err_fun(double *nom_x, double *delta_x, double *out_1624039058015520117) {
   out_1624039058015520117[0] = delta_x[0] + nom_x[0];
   out_1624039058015520117[1] = delta_x[1] + nom_x[1];
   out_1624039058015520117[2] = delta_x[2] + nom_x[2];
   out_1624039058015520117[3] = delta_x[3] + nom_x[3];
   out_1624039058015520117[4] = delta_x[4] + nom_x[4];
   out_1624039058015520117[5] = delta_x[5] + nom_x[5];
   out_1624039058015520117[6] = delta_x[6] + nom_x[6];
   out_1624039058015520117[7] = delta_x[7] + nom_x[7];
   out_1624039058015520117[8] = delta_x[8] + nom_x[8];
   out_1624039058015520117[9] = delta_x[9] + nom_x[9];
   out_1624039058015520117[10] = delta_x[10] + nom_x[10];
   out_1624039058015520117[11] = delta_x[11] + nom_x[11];
   out_1624039058015520117[12] = delta_x[12] + nom_x[12];
   out_1624039058015520117[13] = delta_x[13] + nom_x[13];
   out_1624039058015520117[14] = delta_x[14] + nom_x[14];
   out_1624039058015520117[15] = delta_x[15] + nom_x[15];
   out_1624039058015520117[16] = delta_x[16] + nom_x[16];
   out_1624039058015520117[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3394922841093355008) {
   out_3394922841093355008[0] = -nom_x[0] + true_x[0];
   out_3394922841093355008[1] = -nom_x[1] + true_x[1];
   out_3394922841093355008[2] = -nom_x[2] + true_x[2];
   out_3394922841093355008[3] = -nom_x[3] + true_x[3];
   out_3394922841093355008[4] = -nom_x[4] + true_x[4];
   out_3394922841093355008[5] = -nom_x[5] + true_x[5];
   out_3394922841093355008[6] = -nom_x[6] + true_x[6];
   out_3394922841093355008[7] = -nom_x[7] + true_x[7];
   out_3394922841093355008[8] = -nom_x[8] + true_x[8];
   out_3394922841093355008[9] = -nom_x[9] + true_x[9];
   out_3394922841093355008[10] = -nom_x[10] + true_x[10];
   out_3394922841093355008[11] = -nom_x[11] + true_x[11];
   out_3394922841093355008[12] = -nom_x[12] + true_x[12];
   out_3394922841093355008[13] = -nom_x[13] + true_x[13];
   out_3394922841093355008[14] = -nom_x[14] + true_x[14];
   out_3394922841093355008[15] = -nom_x[15] + true_x[15];
   out_3394922841093355008[16] = -nom_x[16] + true_x[16];
   out_3394922841093355008[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5983346335611634108) {
   out_5983346335611634108[0] = 1.0;
   out_5983346335611634108[1] = 0.0;
   out_5983346335611634108[2] = 0.0;
   out_5983346335611634108[3] = 0.0;
   out_5983346335611634108[4] = 0.0;
   out_5983346335611634108[5] = 0.0;
   out_5983346335611634108[6] = 0.0;
   out_5983346335611634108[7] = 0.0;
   out_5983346335611634108[8] = 0.0;
   out_5983346335611634108[9] = 0.0;
   out_5983346335611634108[10] = 0.0;
   out_5983346335611634108[11] = 0.0;
   out_5983346335611634108[12] = 0.0;
   out_5983346335611634108[13] = 0.0;
   out_5983346335611634108[14] = 0.0;
   out_5983346335611634108[15] = 0.0;
   out_5983346335611634108[16] = 0.0;
   out_5983346335611634108[17] = 0.0;
   out_5983346335611634108[18] = 0.0;
   out_5983346335611634108[19] = 1.0;
   out_5983346335611634108[20] = 0.0;
   out_5983346335611634108[21] = 0.0;
   out_5983346335611634108[22] = 0.0;
   out_5983346335611634108[23] = 0.0;
   out_5983346335611634108[24] = 0.0;
   out_5983346335611634108[25] = 0.0;
   out_5983346335611634108[26] = 0.0;
   out_5983346335611634108[27] = 0.0;
   out_5983346335611634108[28] = 0.0;
   out_5983346335611634108[29] = 0.0;
   out_5983346335611634108[30] = 0.0;
   out_5983346335611634108[31] = 0.0;
   out_5983346335611634108[32] = 0.0;
   out_5983346335611634108[33] = 0.0;
   out_5983346335611634108[34] = 0.0;
   out_5983346335611634108[35] = 0.0;
   out_5983346335611634108[36] = 0.0;
   out_5983346335611634108[37] = 0.0;
   out_5983346335611634108[38] = 1.0;
   out_5983346335611634108[39] = 0.0;
   out_5983346335611634108[40] = 0.0;
   out_5983346335611634108[41] = 0.0;
   out_5983346335611634108[42] = 0.0;
   out_5983346335611634108[43] = 0.0;
   out_5983346335611634108[44] = 0.0;
   out_5983346335611634108[45] = 0.0;
   out_5983346335611634108[46] = 0.0;
   out_5983346335611634108[47] = 0.0;
   out_5983346335611634108[48] = 0.0;
   out_5983346335611634108[49] = 0.0;
   out_5983346335611634108[50] = 0.0;
   out_5983346335611634108[51] = 0.0;
   out_5983346335611634108[52] = 0.0;
   out_5983346335611634108[53] = 0.0;
   out_5983346335611634108[54] = 0.0;
   out_5983346335611634108[55] = 0.0;
   out_5983346335611634108[56] = 0.0;
   out_5983346335611634108[57] = 1.0;
   out_5983346335611634108[58] = 0.0;
   out_5983346335611634108[59] = 0.0;
   out_5983346335611634108[60] = 0.0;
   out_5983346335611634108[61] = 0.0;
   out_5983346335611634108[62] = 0.0;
   out_5983346335611634108[63] = 0.0;
   out_5983346335611634108[64] = 0.0;
   out_5983346335611634108[65] = 0.0;
   out_5983346335611634108[66] = 0.0;
   out_5983346335611634108[67] = 0.0;
   out_5983346335611634108[68] = 0.0;
   out_5983346335611634108[69] = 0.0;
   out_5983346335611634108[70] = 0.0;
   out_5983346335611634108[71] = 0.0;
   out_5983346335611634108[72] = 0.0;
   out_5983346335611634108[73] = 0.0;
   out_5983346335611634108[74] = 0.0;
   out_5983346335611634108[75] = 0.0;
   out_5983346335611634108[76] = 1.0;
   out_5983346335611634108[77] = 0.0;
   out_5983346335611634108[78] = 0.0;
   out_5983346335611634108[79] = 0.0;
   out_5983346335611634108[80] = 0.0;
   out_5983346335611634108[81] = 0.0;
   out_5983346335611634108[82] = 0.0;
   out_5983346335611634108[83] = 0.0;
   out_5983346335611634108[84] = 0.0;
   out_5983346335611634108[85] = 0.0;
   out_5983346335611634108[86] = 0.0;
   out_5983346335611634108[87] = 0.0;
   out_5983346335611634108[88] = 0.0;
   out_5983346335611634108[89] = 0.0;
   out_5983346335611634108[90] = 0.0;
   out_5983346335611634108[91] = 0.0;
   out_5983346335611634108[92] = 0.0;
   out_5983346335611634108[93] = 0.0;
   out_5983346335611634108[94] = 0.0;
   out_5983346335611634108[95] = 1.0;
   out_5983346335611634108[96] = 0.0;
   out_5983346335611634108[97] = 0.0;
   out_5983346335611634108[98] = 0.0;
   out_5983346335611634108[99] = 0.0;
   out_5983346335611634108[100] = 0.0;
   out_5983346335611634108[101] = 0.0;
   out_5983346335611634108[102] = 0.0;
   out_5983346335611634108[103] = 0.0;
   out_5983346335611634108[104] = 0.0;
   out_5983346335611634108[105] = 0.0;
   out_5983346335611634108[106] = 0.0;
   out_5983346335611634108[107] = 0.0;
   out_5983346335611634108[108] = 0.0;
   out_5983346335611634108[109] = 0.0;
   out_5983346335611634108[110] = 0.0;
   out_5983346335611634108[111] = 0.0;
   out_5983346335611634108[112] = 0.0;
   out_5983346335611634108[113] = 0.0;
   out_5983346335611634108[114] = 1.0;
   out_5983346335611634108[115] = 0.0;
   out_5983346335611634108[116] = 0.0;
   out_5983346335611634108[117] = 0.0;
   out_5983346335611634108[118] = 0.0;
   out_5983346335611634108[119] = 0.0;
   out_5983346335611634108[120] = 0.0;
   out_5983346335611634108[121] = 0.0;
   out_5983346335611634108[122] = 0.0;
   out_5983346335611634108[123] = 0.0;
   out_5983346335611634108[124] = 0.0;
   out_5983346335611634108[125] = 0.0;
   out_5983346335611634108[126] = 0.0;
   out_5983346335611634108[127] = 0.0;
   out_5983346335611634108[128] = 0.0;
   out_5983346335611634108[129] = 0.0;
   out_5983346335611634108[130] = 0.0;
   out_5983346335611634108[131] = 0.0;
   out_5983346335611634108[132] = 0.0;
   out_5983346335611634108[133] = 1.0;
   out_5983346335611634108[134] = 0.0;
   out_5983346335611634108[135] = 0.0;
   out_5983346335611634108[136] = 0.0;
   out_5983346335611634108[137] = 0.0;
   out_5983346335611634108[138] = 0.0;
   out_5983346335611634108[139] = 0.0;
   out_5983346335611634108[140] = 0.0;
   out_5983346335611634108[141] = 0.0;
   out_5983346335611634108[142] = 0.0;
   out_5983346335611634108[143] = 0.0;
   out_5983346335611634108[144] = 0.0;
   out_5983346335611634108[145] = 0.0;
   out_5983346335611634108[146] = 0.0;
   out_5983346335611634108[147] = 0.0;
   out_5983346335611634108[148] = 0.0;
   out_5983346335611634108[149] = 0.0;
   out_5983346335611634108[150] = 0.0;
   out_5983346335611634108[151] = 0.0;
   out_5983346335611634108[152] = 1.0;
   out_5983346335611634108[153] = 0.0;
   out_5983346335611634108[154] = 0.0;
   out_5983346335611634108[155] = 0.0;
   out_5983346335611634108[156] = 0.0;
   out_5983346335611634108[157] = 0.0;
   out_5983346335611634108[158] = 0.0;
   out_5983346335611634108[159] = 0.0;
   out_5983346335611634108[160] = 0.0;
   out_5983346335611634108[161] = 0.0;
   out_5983346335611634108[162] = 0.0;
   out_5983346335611634108[163] = 0.0;
   out_5983346335611634108[164] = 0.0;
   out_5983346335611634108[165] = 0.0;
   out_5983346335611634108[166] = 0.0;
   out_5983346335611634108[167] = 0.0;
   out_5983346335611634108[168] = 0.0;
   out_5983346335611634108[169] = 0.0;
   out_5983346335611634108[170] = 0.0;
   out_5983346335611634108[171] = 1.0;
   out_5983346335611634108[172] = 0.0;
   out_5983346335611634108[173] = 0.0;
   out_5983346335611634108[174] = 0.0;
   out_5983346335611634108[175] = 0.0;
   out_5983346335611634108[176] = 0.0;
   out_5983346335611634108[177] = 0.0;
   out_5983346335611634108[178] = 0.0;
   out_5983346335611634108[179] = 0.0;
   out_5983346335611634108[180] = 0.0;
   out_5983346335611634108[181] = 0.0;
   out_5983346335611634108[182] = 0.0;
   out_5983346335611634108[183] = 0.0;
   out_5983346335611634108[184] = 0.0;
   out_5983346335611634108[185] = 0.0;
   out_5983346335611634108[186] = 0.0;
   out_5983346335611634108[187] = 0.0;
   out_5983346335611634108[188] = 0.0;
   out_5983346335611634108[189] = 0.0;
   out_5983346335611634108[190] = 1.0;
   out_5983346335611634108[191] = 0.0;
   out_5983346335611634108[192] = 0.0;
   out_5983346335611634108[193] = 0.0;
   out_5983346335611634108[194] = 0.0;
   out_5983346335611634108[195] = 0.0;
   out_5983346335611634108[196] = 0.0;
   out_5983346335611634108[197] = 0.0;
   out_5983346335611634108[198] = 0.0;
   out_5983346335611634108[199] = 0.0;
   out_5983346335611634108[200] = 0.0;
   out_5983346335611634108[201] = 0.0;
   out_5983346335611634108[202] = 0.0;
   out_5983346335611634108[203] = 0.0;
   out_5983346335611634108[204] = 0.0;
   out_5983346335611634108[205] = 0.0;
   out_5983346335611634108[206] = 0.0;
   out_5983346335611634108[207] = 0.0;
   out_5983346335611634108[208] = 0.0;
   out_5983346335611634108[209] = 1.0;
   out_5983346335611634108[210] = 0.0;
   out_5983346335611634108[211] = 0.0;
   out_5983346335611634108[212] = 0.0;
   out_5983346335611634108[213] = 0.0;
   out_5983346335611634108[214] = 0.0;
   out_5983346335611634108[215] = 0.0;
   out_5983346335611634108[216] = 0.0;
   out_5983346335611634108[217] = 0.0;
   out_5983346335611634108[218] = 0.0;
   out_5983346335611634108[219] = 0.0;
   out_5983346335611634108[220] = 0.0;
   out_5983346335611634108[221] = 0.0;
   out_5983346335611634108[222] = 0.0;
   out_5983346335611634108[223] = 0.0;
   out_5983346335611634108[224] = 0.0;
   out_5983346335611634108[225] = 0.0;
   out_5983346335611634108[226] = 0.0;
   out_5983346335611634108[227] = 0.0;
   out_5983346335611634108[228] = 1.0;
   out_5983346335611634108[229] = 0.0;
   out_5983346335611634108[230] = 0.0;
   out_5983346335611634108[231] = 0.0;
   out_5983346335611634108[232] = 0.0;
   out_5983346335611634108[233] = 0.0;
   out_5983346335611634108[234] = 0.0;
   out_5983346335611634108[235] = 0.0;
   out_5983346335611634108[236] = 0.0;
   out_5983346335611634108[237] = 0.0;
   out_5983346335611634108[238] = 0.0;
   out_5983346335611634108[239] = 0.0;
   out_5983346335611634108[240] = 0.0;
   out_5983346335611634108[241] = 0.0;
   out_5983346335611634108[242] = 0.0;
   out_5983346335611634108[243] = 0.0;
   out_5983346335611634108[244] = 0.0;
   out_5983346335611634108[245] = 0.0;
   out_5983346335611634108[246] = 0.0;
   out_5983346335611634108[247] = 1.0;
   out_5983346335611634108[248] = 0.0;
   out_5983346335611634108[249] = 0.0;
   out_5983346335611634108[250] = 0.0;
   out_5983346335611634108[251] = 0.0;
   out_5983346335611634108[252] = 0.0;
   out_5983346335611634108[253] = 0.0;
   out_5983346335611634108[254] = 0.0;
   out_5983346335611634108[255] = 0.0;
   out_5983346335611634108[256] = 0.0;
   out_5983346335611634108[257] = 0.0;
   out_5983346335611634108[258] = 0.0;
   out_5983346335611634108[259] = 0.0;
   out_5983346335611634108[260] = 0.0;
   out_5983346335611634108[261] = 0.0;
   out_5983346335611634108[262] = 0.0;
   out_5983346335611634108[263] = 0.0;
   out_5983346335611634108[264] = 0.0;
   out_5983346335611634108[265] = 0.0;
   out_5983346335611634108[266] = 1.0;
   out_5983346335611634108[267] = 0.0;
   out_5983346335611634108[268] = 0.0;
   out_5983346335611634108[269] = 0.0;
   out_5983346335611634108[270] = 0.0;
   out_5983346335611634108[271] = 0.0;
   out_5983346335611634108[272] = 0.0;
   out_5983346335611634108[273] = 0.0;
   out_5983346335611634108[274] = 0.0;
   out_5983346335611634108[275] = 0.0;
   out_5983346335611634108[276] = 0.0;
   out_5983346335611634108[277] = 0.0;
   out_5983346335611634108[278] = 0.0;
   out_5983346335611634108[279] = 0.0;
   out_5983346335611634108[280] = 0.0;
   out_5983346335611634108[281] = 0.0;
   out_5983346335611634108[282] = 0.0;
   out_5983346335611634108[283] = 0.0;
   out_5983346335611634108[284] = 0.0;
   out_5983346335611634108[285] = 1.0;
   out_5983346335611634108[286] = 0.0;
   out_5983346335611634108[287] = 0.0;
   out_5983346335611634108[288] = 0.0;
   out_5983346335611634108[289] = 0.0;
   out_5983346335611634108[290] = 0.0;
   out_5983346335611634108[291] = 0.0;
   out_5983346335611634108[292] = 0.0;
   out_5983346335611634108[293] = 0.0;
   out_5983346335611634108[294] = 0.0;
   out_5983346335611634108[295] = 0.0;
   out_5983346335611634108[296] = 0.0;
   out_5983346335611634108[297] = 0.0;
   out_5983346335611634108[298] = 0.0;
   out_5983346335611634108[299] = 0.0;
   out_5983346335611634108[300] = 0.0;
   out_5983346335611634108[301] = 0.0;
   out_5983346335611634108[302] = 0.0;
   out_5983346335611634108[303] = 0.0;
   out_5983346335611634108[304] = 1.0;
   out_5983346335611634108[305] = 0.0;
   out_5983346335611634108[306] = 0.0;
   out_5983346335611634108[307] = 0.0;
   out_5983346335611634108[308] = 0.0;
   out_5983346335611634108[309] = 0.0;
   out_5983346335611634108[310] = 0.0;
   out_5983346335611634108[311] = 0.0;
   out_5983346335611634108[312] = 0.0;
   out_5983346335611634108[313] = 0.0;
   out_5983346335611634108[314] = 0.0;
   out_5983346335611634108[315] = 0.0;
   out_5983346335611634108[316] = 0.0;
   out_5983346335611634108[317] = 0.0;
   out_5983346335611634108[318] = 0.0;
   out_5983346335611634108[319] = 0.0;
   out_5983346335611634108[320] = 0.0;
   out_5983346335611634108[321] = 0.0;
   out_5983346335611634108[322] = 0.0;
   out_5983346335611634108[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_2787475759251093193) {
   out_2787475759251093193[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_2787475759251093193[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_2787475759251093193[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_2787475759251093193[3] = dt*state[12] + state[3];
   out_2787475759251093193[4] = dt*state[13] + state[4];
   out_2787475759251093193[5] = dt*state[14] + state[5];
   out_2787475759251093193[6] = state[6];
   out_2787475759251093193[7] = state[7];
   out_2787475759251093193[8] = state[8];
   out_2787475759251093193[9] = state[9];
   out_2787475759251093193[10] = state[10];
   out_2787475759251093193[11] = state[11];
   out_2787475759251093193[12] = state[12];
   out_2787475759251093193[13] = state[13];
   out_2787475759251093193[14] = state[14];
   out_2787475759251093193[15] = state[15];
   out_2787475759251093193[16] = state[16];
   out_2787475759251093193[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3131463405263695248) {
   out_3131463405263695248[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3131463405263695248[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3131463405263695248[2] = 0;
   out_3131463405263695248[3] = 0;
   out_3131463405263695248[4] = 0;
   out_3131463405263695248[5] = 0;
   out_3131463405263695248[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3131463405263695248[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3131463405263695248[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3131463405263695248[9] = 0;
   out_3131463405263695248[10] = 0;
   out_3131463405263695248[11] = 0;
   out_3131463405263695248[12] = 0;
   out_3131463405263695248[13] = 0;
   out_3131463405263695248[14] = 0;
   out_3131463405263695248[15] = 0;
   out_3131463405263695248[16] = 0;
   out_3131463405263695248[17] = 0;
   out_3131463405263695248[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3131463405263695248[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3131463405263695248[20] = 0;
   out_3131463405263695248[21] = 0;
   out_3131463405263695248[22] = 0;
   out_3131463405263695248[23] = 0;
   out_3131463405263695248[24] = 0;
   out_3131463405263695248[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3131463405263695248[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3131463405263695248[27] = 0;
   out_3131463405263695248[28] = 0;
   out_3131463405263695248[29] = 0;
   out_3131463405263695248[30] = 0;
   out_3131463405263695248[31] = 0;
   out_3131463405263695248[32] = 0;
   out_3131463405263695248[33] = 0;
   out_3131463405263695248[34] = 0;
   out_3131463405263695248[35] = 0;
   out_3131463405263695248[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3131463405263695248[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3131463405263695248[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3131463405263695248[39] = 0;
   out_3131463405263695248[40] = 0;
   out_3131463405263695248[41] = 0;
   out_3131463405263695248[42] = 0;
   out_3131463405263695248[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3131463405263695248[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3131463405263695248[45] = 0;
   out_3131463405263695248[46] = 0;
   out_3131463405263695248[47] = 0;
   out_3131463405263695248[48] = 0;
   out_3131463405263695248[49] = 0;
   out_3131463405263695248[50] = 0;
   out_3131463405263695248[51] = 0;
   out_3131463405263695248[52] = 0;
   out_3131463405263695248[53] = 0;
   out_3131463405263695248[54] = 0;
   out_3131463405263695248[55] = 0;
   out_3131463405263695248[56] = 0;
   out_3131463405263695248[57] = 1;
   out_3131463405263695248[58] = 0;
   out_3131463405263695248[59] = 0;
   out_3131463405263695248[60] = 0;
   out_3131463405263695248[61] = 0;
   out_3131463405263695248[62] = 0;
   out_3131463405263695248[63] = 0;
   out_3131463405263695248[64] = 0;
   out_3131463405263695248[65] = 0;
   out_3131463405263695248[66] = dt;
   out_3131463405263695248[67] = 0;
   out_3131463405263695248[68] = 0;
   out_3131463405263695248[69] = 0;
   out_3131463405263695248[70] = 0;
   out_3131463405263695248[71] = 0;
   out_3131463405263695248[72] = 0;
   out_3131463405263695248[73] = 0;
   out_3131463405263695248[74] = 0;
   out_3131463405263695248[75] = 0;
   out_3131463405263695248[76] = 1;
   out_3131463405263695248[77] = 0;
   out_3131463405263695248[78] = 0;
   out_3131463405263695248[79] = 0;
   out_3131463405263695248[80] = 0;
   out_3131463405263695248[81] = 0;
   out_3131463405263695248[82] = 0;
   out_3131463405263695248[83] = 0;
   out_3131463405263695248[84] = 0;
   out_3131463405263695248[85] = dt;
   out_3131463405263695248[86] = 0;
   out_3131463405263695248[87] = 0;
   out_3131463405263695248[88] = 0;
   out_3131463405263695248[89] = 0;
   out_3131463405263695248[90] = 0;
   out_3131463405263695248[91] = 0;
   out_3131463405263695248[92] = 0;
   out_3131463405263695248[93] = 0;
   out_3131463405263695248[94] = 0;
   out_3131463405263695248[95] = 1;
   out_3131463405263695248[96] = 0;
   out_3131463405263695248[97] = 0;
   out_3131463405263695248[98] = 0;
   out_3131463405263695248[99] = 0;
   out_3131463405263695248[100] = 0;
   out_3131463405263695248[101] = 0;
   out_3131463405263695248[102] = 0;
   out_3131463405263695248[103] = 0;
   out_3131463405263695248[104] = dt;
   out_3131463405263695248[105] = 0;
   out_3131463405263695248[106] = 0;
   out_3131463405263695248[107] = 0;
   out_3131463405263695248[108] = 0;
   out_3131463405263695248[109] = 0;
   out_3131463405263695248[110] = 0;
   out_3131463405263695248[111] = 0;
   out_3131463405263695248[112] = 0;
   out_3131463405263695248[113] = 0;
   out_3131463405263695248[114] = 1;
   out_3131463405263695248[115] = 0;
   out_3131463405263695248[116] = 0;
   out_3131463405263695248[117] = 0;
   out_3131463405263695248[118] = 0;
   out_3131463405263695248[119] = 0;
   out_3131463405263695248[120] = 0;
   out_3131463405263695248[121] = 0;
   out_3131463405263695248[122] = 0;
   out_3131463405263695248[123] = 0;
   out_3131463405263695248[124] = 0;
   out_3131463405263695248[125] = 0;
   out_3131463405263695248[126] = 0;
   out_3131463405263695248[127] = 0;
   out_3131463405263695248[128] = 0;
   out_3131463405263695248[129] = 0;
   out_3131463405263695248[130] = 0;
   out_3131463405263695248[131] = 0;
   out_3131463405263695248[132] = 0;
   out_3131463405263695248[133] = 1;
   out_3131463405263695248[134] = 0;
   out_3131463405263695248[135] = 0;
   out_3131463405263695248[136] = 0;
   out_3131463405263695248[137] = 0;
   out_3131463405263695248[138] = 0;
   out_3131463405263695248[139] = 0;
   out_3131463405263695248[140] = 0;
   out_3131463405263695248[141] = 0;
   out_3131463405263695248[142] = 0;
   out_3131463405263695248[143] = 0;
   out_3131463405263695248[144] = 0;
   out_3131463405263695248[145] = 0;
   out_3131463405263695248[146] = 0;
   out_3131463405263695248[147] = 0;
   out_3131463405263695248[148] = 0;
   out_3131463405263695248[149] = 0;
   out_3131463405263695248[150] = 0;
   out_3131463405263695248[151] = 0;
   out_3131463405263695248[152] = 1;
   out_3131463405263695248[153] = 0;
   out_3131463405263695248[154] = 0;
   out_3131463405263695248[155] = 0;
   out_3131463405263695248[156] = 0;
   out_3131463405263695248[157] = 0;
   out_3131463405263695248[158] = 0;
   out_3131463405263695248[159] = 0;
   out_3131463405263695248[160] = 0;
   out_3131463405263695248[161] = 0;
   out_3131463405263695248[162] = 0;
   out_3131463405263695248[163] = 0;
   out_3131463405263695248[164] = 0;
   out_3131463405263695248[165] = 0;
   out_3131463405263695248[166] = 0;
   out_3131463405263695248[167] = 0;
   out_3131463405263695248[168] = 0;
   out_3131463405263695248[169] = 0;
   out_3131463405263695248[170] = 0;
   out_3131463405263695248[171] = 1;
   out_3131463405263695248[172] = 0;
   out_3131463405263695248[173] = 0;
   out_3131463405263695248[174] = 0;
   out_3131463405263695248[175] = 0;
   out_3131463405263695248[176] = 0;
   out_3131463405263695248[177] = 0;
   out_3131463405263695248[178] = 0;
   out_3131463405263695248[179] = 0;
   out_3131463405263695248[180] = 0;
   out_3131463405263695248[181] = 0;
   out_3131463405263695248[182] = 0;
   out_3131463405263695248[183] = 0;
   out_3131463405263695248[184] = 0;
   out_3131463405263695248[185] = 0;
   out_3131463405263695248[186] = 0;
   out_3131463405263695248[187] = 0;
   out_3131463405263695248[188] = 0;
   out_3131463405263695248[189] = 0;
   out_3131463405263695248[190] = 1;
   out_3131463405263695248[191] = 0;
   out_3131463405263695248[192] = 0;
   out_3131463405263695248[193] = 0;
   out_3131463405263695248[194] = 0;
   out_3131463405263695248[195] = 0;
   out_3131463405263695248[196] = 0;
   out_3131463405263695248[197] = 0;
   out_3131463405263695248[198] = 0;
   out_3131463405263695248[199] = 0;
   out_3131463405263695248[200] = 0;
   out_3131463405263695248[201] = 0;
   out_3131463405263695248[202] = 0;
   out_3131463405263695248[203] = 0;
   out_3131463405263695248[204] = 0;
   out_3131463405263695248[205] = 0;
   out_3131463405263695248[206] = 0;
   out_3131463405263695248[207] = 0;
   out_3131463405263695248[208] = 0;
   out_3131463405263695248[209] = 1;
   out_3131463405263695248[210] = 0;
   out_3131463405263695248[211] = 0;
   out_3131463405263695248[212] = 0;
   out_3131463405263695248[213] = 0;
   out_3131463405263695248[214] = 0;
   out_3131463405263695248[215] = 0;
   out_3131463405263695248[216] = 0;
   out_3131463405263695248[217] = 0;
   out_3131463405263695248[218] = 0;
   out_3131463405263695248[219] = 0;
   out_3131463405263695248[220] = 0;
   out_3131463405263695248[221] = 0;
   out_3131463405263695248[222] = 0;
   out_3131463405263695248[223] = 0;
   out_3131463405263695248[224] = 0;
   out_3131463405263695248[225] = 0;
   out_3131463405263695248[226] = 0;
   out_3131463405263695248[227] = 0;
   out_3131463405263695248[228] = 1;
   out_3131463405263695248[229] = 0;
   out_3131463405263695248[230] = 0;
   out_3131463405263695248[231] = 0;
   out_3131463405263695248[232] = 0;
   out_3131463405263695248[233] = 0;
   out_3131463405263695248[234] = 0;
   out_3131463405263695248[235] = 0;
   out_3131463405263695248[236] = 0;
   out_3131463405263695248[237] = 0;
   out_3131463405263695248[238] = 0;
   out_3131463405263695248[239] = 0;
   out_3131463405263695248[240] = 0;
   out_3131463405263695248[241] = 0;
   out_3131463405263695248[242] = 0;
   out_3131463405263695248[243] = 0;
   out_3131463405263695248[244] = 0;
   out_3131463405263695248[245] = 0;
   out_3131463405263695248[246] = 0;
   out_3131463405263695248[247] = 1;
   out_3131463405263695248[248] = 0;
   out_3131463405263695248[249] = 0;
   out_3131463405263695248[250] = 0;
   out_3131463405263695248[251] = 0;
   out_3131463405263695248[252] = 0;
   out_3131463405263695248[253] = 0;
   out_3131463405263695248[254] = 0;
   out_3131463405263695248[255] = 0;
   out_3131463405263695248[256] = 0;
   out_3131463405263695248[257] = 0;
   out_3131463405263695248[258] = 0;
   out_3131463405263695248[259] = 0;
   out_3131463405263695248[260] = 0;
   out_3131463405263695248[261] = 0;
   out_3131463405263695248[262] = 0;
   out_3131463405263695248[263] = 0;
   out_3131463405263695248[264] = 0;
   out_3131463405263695248[265] = 0;
   out_3131463405263695248[266] = 1;
   out_3131463405263695248[267] = 0;
   out_3131463405263695248[268] = 0;
   out_3131463405263695248[269] = 0;
   out_3131463405263695248[270] = 0;
   out_3131463405263695248[271] = 0;
   out_3131463405263695248[272] = 0;
   out_3131463405263695248[273] = 0;
   out_3131463405263695248[274] = 0;
   out_3131463405263695248[275] = 0;
   out_3131463405263695248[276] = 0;
   out_3131463405263695248[277] = 0;
   out_3131463405263695248[278] = 0;
   out_3131463405263695248[279] = 0;
   out_3131463405263695248[280] = 0;
   out_3131463405263695248[281] = 0;
   out_3131463405263695248[282] = 0;
   out_3131463405263695248[283] = 0;
   out_3131463405263695248[284] = 0;
   out_3131463405263695248[285] = 1;
   out_3131463405263695248[286] = 0;
   out_3131463405263695248[287] = 0;
   out_3131463405263695248[288] = 0;
   out_3131463405263695248[289] = 0;
   out_3131463405263695248[290] = 0;
   out_3131463405263695248[291] = 0;
   out_3131463405263695248[292] = 0;
   out_3131463405263695248[293] = 0;
   out_3131463405263695248[294] = 0;
   out_3131463405263695248[295] = 0;
   out_3131463405263695248[296] = 0;
   out_3131463405263695248[297] = 0;
   out_3131463405263695248[298] = 0;
   out_3131463405263695248[299] = 0;
   out_3131463405263695248[300] = 0;
   out_3131463405263695248[301] = 0;
   out_3131463405263695248[302] = 0;
   out_3131463405263695248[303] = 0;
   out_3131463405263695248[304] = 1;
   out_3131463405263695248[305] = 0;
   out_3131463405263695248[306] = 0;
   out_3131463405263695248[307] = 0;
   out_3131463405263695248[308] = 0;
   out_3131463405263695248[309] = 0;
   out_3131463405263695248[310] = 0;
   out_3131463405263695248[311] = 0;
   out_3131463405263695248[312] = 0;
   out_3131463405263695248[313] = 0;
   out_3131463405263695248[314] = 0;
   out_3131463405263695248[315] = 0;
   out_3131463405263695248[316] = 0;
   out_3131463405263695248[317] = 0;
   out_3131463405263695248[318] = 0;
   out_3131463405263695248[319] = 0;
   out_3131463405263695248[320] = 0;
   out_3131463405263695248[321] = 0;
   out_3131463405263695248[322] = 0;
   out_3131463405263695248[323] = 1;
}
void h_4(double *state, double *unused, double *out_4236476822836846053) {
   out_4236476822836846053[0] = state[6] + state[9];
   out_4236476822836846053[1] = state[7] + state[10];
   out_4236476822836846053[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_135264528859675387) {
   out_135264528859675387[0] = 0;
   out_135264528859675387[1] = 0;
   out_135264528859675387[2] = 0;
   out_135264528859675387[3] = 0;
   out_135264528859675387[4] = 0;
   out_135264528859675387[5] = 0;
   out_135264528859675387[6] = 1;
   out_135264528859675387[7] = 0;
   out_135264528859675387[8] = 0;
   out_135264528859675387[9] = 1;
   out_135264528859675387[10] = 0;
   out_135264528859675387[11] = 0;
   out_135264528859675387[12] = 0;
   out_135264528859675387[13] = 0;
   out_135264528859675387[14] = 0;
   out_135264528859675387[15] = 0;
   out_135264528859675387[16] = 0;
   out_135264528859675387[17] = 0;
   out_135264528859675387[18] = 0;
   out_135264528859675387[19] = 0;
   out_135264528859675387[20] = 0;
   out_135264528859675387[21] = 0;
   out_135264528859675387[22] = 0;
   out_135264528859675387[23] = 0;
   out_135264528859675387[24] = 0;
   out_135264528859675387[25] = 1;
   out_135264528859675387[26] = 0;
   out_135264528859675387[27] = 0;
   out_135264528859675387[28] = 1;
   out_135264528859675387[29] = 0;
   out_135264528859675387[30] = 0;
   out_135264528859675387[31] = 0;
   out_135264528859675387[32] = 0;
   out_135264528859675387[33] = 0;
   out_135264528859675387[34] = 0;
   out_135264528859675387[35] = 0;
   out_135264528859675387[36] = 0;
   out_135264528859675387[37] = 0;
   out_135264528859675387[38] = 0;
   out_135264528859675387[39] = 0;
   out_135264528859675387[40] = 0;
   out_135264528859675387[41] = 0;
   out_135264528859675387[42] = 0;
   out_135264528859675387[43] = 0;
   out_135264528859675387[44] = 1;
   out_135264528859675387[45] = 0;
   out_135264528859675387[46] = 0;
   out_135264528859675387[47] = 1;
   out_135264528859675387[48] = 0;
   out_135264528859675387[49] = 0;
   out_135264528859675387[50] = 0;
   out_135264528859675387[51] = 0;
   out_135264528859675387[52] = 0;
   out_135264528859675387[53] = 0;
}
void h_10(double *state, double *unused, double *out_8903764653121362197) {
   out_8903764653121362197[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_8903764653121362197[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_8903764653121362197[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6671785341230841941) {
   out_6671785341230841941[0] = 0;
   out_6671785341230841941[1] = 9.8100000000000005*cos(state[1]);
   out_6671785341230841941[2] = 0;
   out_6671785341230841941[3] = 0;
   out_6671785341230841941[4] = -state[8];
   out_6671785341230841941[5] = state[7];
   out_6671785341230841941[6] = 0;
   out_6671785341230841941[7] = state[5];
   out_6671785341230841941[8] = -state[4];
   out_6671785341230841941[9] = 0;
   out_6671785341230841941[10] = 0;
   out_6671785341230841941[11] = 0;
   out_6671785341230841941[12] = 1;
   out_6671785341230841941[13] = 0;
   out_6671785341230841941[14] = 0;
   out_6671785341230841941[15] = 1;
   out_6671785341230841941[16] = 0;
   out_6671785341230841941[17] = 0;
   out_6671785341230841941[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6671785341230841941[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6671785341230841941[20] = 0;
   out_6671785341230841941[21] = state[8];
   out_6671785341230841941[22] = 0;
   out_6671785341230841941[23] = -state[6];
   out_6671785341230841941[24] = -state[5];
   out_6671785341230841941[25] = 0;
   out_6671785341230841941[26] = state[3];
   out_6671785341230841941[27] = 0;
   out_6671785341230841941[28] = 0;
   out_6671785341230841941[29] = 0;
   out_6671785341230841941[30] = 0;
   out_6671785341230841941[31] = 1;
   out_6671785341230841941[32] = 0;
   out_6671785341230841941[33] = 0;
   out_6671785341230841941[34] = 1;
   out_6671785341230841941[35] = 0;
   out_6671785341230841941[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6671785341230841941[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6671785341230841941[38] = 0;
   out_6671785341230841941[39] = -state[7];
   out_6671785341230841941[40] = state[6];
   out_6671785341230841941[41] = 0;
   out_6671785341230841941[42] = state[4];
   out_6671785341230841941[43] = -state[3];
   out_6671785341230841941[44] = 0;
   out_6671785341230841941[45] = 0;
   out_6671785341230841941[46] = 0;
   out_6671785341230841941[47] = 0;
   out_6671785341230841941[48] = 0;
   out_6671785341230841941[49] = 0;
   out_6671785341230841941[50] = 1;
   out_6671785341230841941[51] = 0;
   out_6671785341230841941[52] = 0;
   out_6671785341230841941[53] = 1;
}
void h_13(double *state, double *unused, double *out_6817806490457608280) {
   out_6817806490457608280[0] = state[3];
   out_6817806490457608280[1] = state[4];
   out_6817806490457608280[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3347538354192008188) {
   out_3347538354192008188[0] = 0;
   out_3347538354192008188[1] = 0;
   out_3347538354192008188[2] = 0;
   out_3347538354192008188[3] = 1;
   out_3347538354192008188[4] = 0;
   out_3347538354192008188[5] = 0;
   out_3347538354192008188[6] = 0;
   out_3347538354192008188[7] = 0;
   out_3347538354192008188[8] = 0;
   out_3347538354192008188[9] = 0;
   out_3347538354192008188[10] = 0;
   out_3347538354192008188[11] = 0;
   out_3347538354192008188[12] = 0;
   out_3347538354192008188[13] = 0;
   out_3347538354192008188[14] = 0;
   out_3347538354192008188[15] = 0;
   out_3347538354192008188[16] = 0;
   out_3347538354192008188[17] = 0;
   out_3347538354192008188[18] = 0;
   out_3347538354192008188[19] = 0;
   out_3347538354192008188[20] = 0;
   out_3347538354192008188[21] = 0;
   out_3347538354192008188[22] = 1;
   out_3347538354192008188[23] = 0;
   out_3347538354192008188[24] = 0;
   out_3347538354192008188[25] = 0;
   out_3347538354192008188[26] = 0;
   out_3347538354192008188[27] = 0;
   out_3347538354192008188[28] = 0;
   out_3347538354192008188[29] = 0;
   out_3347538354192008188[30] = 0;
   out_3347538354192008188[31] = 0;
   out_3347538354192008188[32] = 0;
   out_3347538354192008188[33] = 0;
   out_3347538354192008188[34] = 0;
   out_3347538354192008188[35] = 0;
   out_3347538354192008188[36] = 0;
   out_3347538354192008188[37] = 0;
   out_3347538354192008188[38] = 0;
   out_3347538354192008188[39] = 0;
   out_3347538354192008188[40] = 0;
   out_3347538354192008188[41] = 1;
   out_3347538354192008188[42] = 0;
   out_3347538354192008188[43] = 0;
   out_3347538354192008188[44] = 0;
   out_3347538354192008188[45] = 0;
   out_3347538354192008188[46] = 0;
   out_3347538354192008188[47] = 0;
   out_3347538354192008188[48] = 0;
   out_3347538354192008188[49] = 0;
   out_3347538354192008188[50] = 0;
   out_3347538354192008188[51] = 0;
   out_3347538354192008188[52] = 0;
   out_3347538354192008188[53] = 0;
}
void h_14(double *state, double *unused, double *out_2340902130253582351) {
   out_2340902130253582351[0] = state[6];
   out_2340902130253582351[1] = state[7];
   out_2340902130253582351[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4098505385199159916) {
   out_4098505385199159916[0] = 0;
   out_4098505385199159916[1] = 0;
   out_4098505385199159916[2] = 0;
   out_4098505385199159916[3] = 0;
   out_4098505385199159916[4] = 0;
   out_4098505385199159916[5] = 0;
   out_4098505385199159916[6] = 1;
   out_4098505385199159916[7] = 0;
   out_4098505385199159916[8] = 0;
   out_4098505385199159916[9] = 0;
   out_4098505385199159916[10] = 0;
   out_4098505385199159916[11] = 0;
   out_4098505385199159916[12] = 0;
   out_4098505385199159916[13] = 0;
   out_4098505385199159916[14] = 0;
   out_4098505385199159916[15] = 0;
   out_4098505385199159916[16] = 0;
   out_4098505385199159916[17] = 0;
   out_4098505385199159916[18] = 0;
   out_4098505385199159916[19] = 0;
   out_4098505385199159916[20] = 0;
   out_4098505385199159916[21] = 0;
   out_4098505385199159916[22] = 0;
   out_4098505385199159916[23] = 0;
   out_4098505385199159916[24] = 0;
   out_4098505385199159916[25] = 1;
   out_4098505385199159916[26] = 0;
   out_4098505385199159916[27] = 0;
   out_4098505385199159916[28] = 0;
   out_4098505385199159916[29] = 0;
   out_4098505385199159916[30] = 0;
   out_4098505385199159916[31] = 0;
   out_4098505385199159916[32] = 0;
   out_4098505385199159916[33] = 0;
   out_4098505385199159916[34] = 0;
   out_4098505385199159916[35] = 0;
   out_4098505385199159916[36] = 0;
   out_4098505385199159916[37] = 0;
   out_4098505385199159916[38] = 0;
   out_4098505385199159916[39] = 0;
   out_4098505385199159916[40] = 0;
   out_4098505385199159916[41] = 0;
   out_4098505385199159916[42] = 0;
   out_4098505385199159916[43] = 0;
   out_4098505385199159916[44] = 1;
   out_4098505385199159916[45] = 0;
   out_4098505385199159916[46] = 0;
   out_4098505385199159916[47] = 0;
   out_4098505385199159916[48] = 0;
   out_4098505385199159916[49] = 0;
   out_4098505385199159916[50] = 0;
   out_4098505385199159916[51] = 0;
   out_4098505385199159916[52] = 0;
   out_4098505385199159916[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_1624039058015520117) {
  err_fun(nom_x, delta_x, out_1624039058015520117);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3394922841093355008) {
  inv_err_fun(nom_x, true_x, out_3394922841093355008);
}
void pose_H_mod_fun(double *state, double *out_5983346335611634108) {
  H_mod_fun(state, out_5983346335611634108);
}
void pose_f_fun(double *state, double dt, double *out_2787475759251093193) {
  f_fun(state,  dt, out_2787475759251093193);
}
void pose_F_fun(double *state, double dt, double *out_3131463405263695248) {
  F_fun(state,  dt, out_3131463405263695248);
}
void pose_h_4(double *state, double *unused, double *out_4236476822836846053) {
  h_4(state, unused, out_4236476822836846053);
}
void pose_H_4(double *state, double *unused, double *out_135264528859675387) {
  H_4(state, unused, out_135264528859675387);
}
void pose_h_10(double *state, double *unused, double *out_8903764653121362197) {
  h_10(state, unused, out_8903764653121362197);
}
void pose_H_10(double *state, double *unused, double *out_6671785341230841941) {
  H_10(state, unused, out_6671785341230841941);
}
void pose_h_13(double *state, double *unused, double *out_6817806490457608280) {
  h_13(state, unused, out_6817806490457608280);
}
void pose_H_13(double *state, double *unused, double *out_3347538354192008188) {
  H_13(state, unused, out_3347538354192008188);
}
void pose_h_14(double *state, double *unused, double *out_2340902130253582351) {
  h_14(state, unused, out_2340902130253582351);
}
void pose_H_14(double *state, double *unused, double *out_4098505385199159916) {
  H_14(state, unused, out_4098505385199159916);
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
