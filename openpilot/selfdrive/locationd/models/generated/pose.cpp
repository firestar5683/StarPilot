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
void err_fun(double *nom_x, double *delta_x, double *out_8769047576014597915) {
   out_8769047576014597915[0] = delta_x[0] + nom_x[0];
   out_8769047576014597915[1] = delta_x[1] + nom_x[1];
   out_8769047576014597915[2] = delta_x[2] + nom_x[2];
   out_8769047576014597915[3] = delta_x[3] + nom_x[3];
   out_8769047576014597915[4] = delta_x[4] + nom_x[4];
   out_8769047576014597915[5] = delta_x[5] + nom_x[5];
   out_8769047576014597915[6] = delta_x[6] + nom_x[6];
   out_8769047576014597915[7] = delta_x[7] + nom_x[7];
   out_8769047576014597915[8] = delta_x[8] + nom_x[8];
   out_8769047576014597915[9] = delta_x[9] + nom_x[9];
   out_8769047576014597915[10] = delta_x[10] + nom_x[10];
   out_8769047576014597915[11] = delta_x[11] + nom_x[11];
   out_8769047576014597915[12] = delta_x[12] + nom_x[12];
   out_8769047576014597915[13] = delta_x[13] + nom_x[13];
   out_8769047576014597915[14] = delta_x[14] + nom_x[14];
   out_8769047576014597915[15] = delta_x[15] + nom_x[15];
   out_8769047576014597915[16] = delta_x[16] + nom_x[16];
   out_8769047576014597915[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6606884682512325288) {
   out_6606884682512325288[0] = -nom_x[0] + true_x[0];
   out_6606884682512325288[1] = -nom_x[1] + true_x[1];
   out_6606884682512325288[2] = -nom_x[2] + true_x[2];
   out_6606884682512325288[3] = -nom_x[3] + true_x[3];
   out_6606884682512325288[4] = -nom_x[4] + true_x[4];
   out_6606884682512325288[5] = -nom_x[5] + true_x[5];
   out_6606884682512325288[6] = -nom_x[6] + true_x[6];
   out_6606884682512325288[7] = -nom_x[7] + true_x[7];
   out_6606884682512325288[8] = -nom_x[8] + true_x[8];
   out_6606884682512325288[9] = -nom_x[9] + true_x[9];
   out_6606884682512325288[10] = -nom_x[10] + true_x[10];
   out_6606884682512325288[11] = -nom_x[11] + true_x[11];
   out_6606884682512325288[12] = -nom_x[12] + true_x[12];
   out_6606884682512325288[13] = -nom_x[13] + true_x[13];
   out_6606884682512325288[14] = -nom_x[14] + true_x[14];
   out_6606884682512325288[15] = -nom_x[15] + true_x[15];
   out_6606884682512325288[16] = -nom_x[16] + true_x[16];
   out_6606884682512325288[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3800934607722013466) {
   out_3800934607722013466[0] = 1.0;
   out_3800934607722013466[1] = 0.0;
   out_3800934607722013466[2] = 0.0;
   out_3800934607722013466[3] = 0.0;
   out_3800934607722013466[4] = 0.0;
   out_3800934607722013466[5] = 0.0;
   out_3800934607722013466[6] = 0.0;
   out_3800934607722013466[7] = 0.0;
   out_3800934607722013466[8] = 0.0;
   out_3800934607722013466[9] = 0.0;
   out_3800934607722013466[10] = 0.0;
   out_3800934607722013466[11] = 0.0;
   out_3800934607722013466[12] = 0.0;
   out_3800934607722013466[13] = 0.0;
   out_3800934607722013466[14] = 0.0;
   out_3800934607722013466[15] = 0.0;
   out_3800934607722013466[16] = 0.0;
   out_3800934607722013466[17] = 0.0;
   out_3800934607722013466[18] = 0.0;
   out_3800934607722013466[19] = 1.0;
   out_3800934607722013466[20] = 0.0;
   out_3800934607722013466[21] = 0.0;
   out_3800934607722013466[22] = 0.0;
   out_3800934607722013466[23] = 0.0;
   out_3800934607722013466[24] = 0.0;
   out_3800934607722013466[25] = 0.0;
   out_3800934607722013466[26] = 0.0;
   out_3800934607722013466[27] = 0.0;
   out_3800934607722013466[28] = 0.0;
   out_3800934607722013466[29] = 0.0;
   out_3800934607722013466[30] = 0.0;
   out_3800934607722013466[31] = 0.0;
   out_3800934607722013466[32] = 0.0;
   out_3800934607722013466[33] = 0.0;
   out_3800934607722013466[34] = 0.0;
   out_3800934607722013466[35] = 0.0;
   out_3800934607722013466[36] = 0.0;
   out_3800934607722013466[37] = 0.0;
   out_3800934607722013466[38] = 1.0;
   out_3800934607722013466[39] = 0.0;
   out_3800934607722013466[40] = 0.0;
   out_3800934607722013466[41] = 0.0;
   out_3800934607722013466[42] = 0.0;
   out_3800934607722013466[43] = 0.0;
   out_3800934607722013466[44] = 0.0;
   out_3800934607722013466[45] = 0.0;
   out_3800934607722013466[46] = 0.0;
   out_3800934607722013466[47] = 0.0;
   out_3800934607722013466[48] = 0.0;
   out_3800934607722013466[49] = 0.0;
   out_3800934607722013466[50] = 0.0;
   out_3800934607722013466[51] = 0.0;
   out_3800934607722013466[52] = 0.0;
   out_3800934607722013466[53] = 0.0;
   out_3800934607722013466[54] = 0.0;
   out_3800934607722013466[55] = 0.0;
   out_3800934607722013466[56] = 0.0;
   out_3800934607722013466[57] = 1.0;
   out_3800934607722013466[58] = 0.0;
   out_3800934607722013466[59] = 0.0;
   out_3800934607722013466[60] = 0.0;
   out_3800934607722013466[61] = 0.0;
   out_3800934607722013466[62] = 0.0;
   out_3800934607722013466[63] = 0.0;
   out_3800934607722013466[64] = 0.0;
   out_3800934607722013466[65] = 0.0;
   out_3800934607722013466[66] = 0.0;
   out_3800934607722013466[67] = 0.0;
   out_3800934607722013466[68] = 0.0;
   out_3800934607722013466[69] = 0.0;
   out_3800934607722013466[70] = 0.0;
   out_3800934607722013466[71] = 0.0;
   out_3800934607722013466[72] = 0.0;
   out_3800934607722013466[73] = 0.0;
   out_3800934607722013466[74] = 0.0;
   out_3800934607722013466[75] = 0.0;
   out_3800934607722013466[76] = 1.0;
   out_3800934607722013466[77] = 0.0;
   out_3800934607722013466[78] = 0.0;
   out_3800934607722013466[79] = 0.0;
   out_3800934607722013466[80] = 0.0;
   out_3800934607722013466[81] = 0.0;
   out_3800934607722013466[82] = 0.0;
   out_3800934607722013466[83] = 0.0;
   out_3800934607722013466[84] = 0.0;
   out_3800934607722013466[85] = 0.0;
   out_3800934607722013466[86] = 0.0;
   out_3800934607722013466[87] = 0.0;
   out_3800934607722013466[88] = 0.0;
   out_3800934607722013466[89] = 0.0;
   out_3800934607722013466[90] = 0.0;
   out_3800934607722013466[91] = 0.0;
   out_3800934607722013466[92] = 0.0;
   out_3800934607722013466[93] = 0.0;
   out_3800934607722013466[94] = 0.0;
   out_3800934607722013466[95] = 1.0;
   out_3800934607722013466[96] = 0.0;
   out_3800934607722013466[97] = 0.0;
   out_3800934607722013466[98] = 0.0;
   out_3800934607722013466[99] = 0.0;
   out_3800934607722013466[100] = 0.0;
   out_3800934607722013466[101] = 0.0;
   out_3800934607722013466[102] = 0.0;
   out_3800934607722013466[103] = 0.0;
   out_3800934607722013466[104] = 0.0;
   out_3800934607722013466[105] = 0.0;
   out_3800934607722013466[106] = 0.0;
   out_3800934607722013466[107] = 0.0;
   out_3800934607722013466[108] = 0.0;
   out_3800934607722013466[109] = 0.0;
   out_3800934607722013466[110] = 0.0;
   out_3800934607722013466[111] = 0.0;
   out_3800934607722013466[112] = 0.0;
   out_3800934607722013466[113] = 0.0;
   out_3800934607722013466[114] = 1.0;
   out_3800934607722013466[115] = 0.0;
   out_3800934607722013466[116] = 0.0;
   out_3800934607722013466[117] = 0.0;
   out_3800934607722013466[118] = 0.0;
   out_3800934607722013466[119] = 0.0;
   out_3800934607722013466[120] = 0.0;
   out_3800934607722013466[121] = 0.0;
   out_3800934607722013466[122] = 0.0;
   out_3800934607722013466[123] = 0.0;
   out_3800934607722013466[124] = 0.0;
   out_3800934607722013466[125] = 0.0;
   out_3800934607722013466[126] = 0.0;
   out_3800934607722013466[127] = 0.0;
   out_3800934607722013466[128] = 0.0;
   out_3800934607722013466[129] = 0.0;
   out_3800934607722013466[130] = 0.0;
   out_3800934607722013466[131] = 0.0;
   out_3800934607722013466[132] = 0.0;
   out_3800934607722013466[133] = 1.0;
   out_3800934607722013466[134] = 0.0;
   out_3800934607722013466[135] = 0.0;
   out_3800934607722013466[136] = 0.0;
   out_3800934607722013466[137] = 0.0;
   out_3800934607722013466[138] = 0.0;
   out_3800934607722013466[139] = 0.0;
   out_3800934607722013466[140] = 0.0;
   out_3800934607722013466[141] = 0.0;
   out_3800934607722013466[142] = 0.0;
   out_3800934607722013466[143] = 0.0;
   out_3800934607722013466[144] = 0.0;
   out_3800934607722013466[145] = 0.0;
   out_3800934607722013466[146] = 0.0;
   out_3800934607722013466[147] = 0.0;
   out_3800934607722013466[148] = 0.0;
   out_3800934607722013466[149] = 0.0;
   out_3800934607722013466[150] = 0.0;
   out_3800934607722013466[151] = 0.0;
   out_3800934607722013466[152] = 1.0;
   out_3800934607722013466[153] = 0.0;
   out_3800934607722013466[154] = 0.0;
   out_3800934607722013466[155] = 0.0;
   out_3800934607722013466[156] = 0.0;
   out_3800934607722013466[157] = 0.0;
   out_3800934607722013466[158] = 0.0;
   out_3800934607722013466[159] = 0.0;
   out_3800934607722013466[160] = 0.0;
   out_3800934607722013466[161] = 0.0;
   out_3800934607722013466[162] = 0.0;
   out_3800934607722013466[163] = 0.0;
   out_3800934607722013466[164] = 0.0;
   out_3800934607722013466[165] = 0.0;
   out_3800934607722013466[166] = 0.0;
   out_3800934607722013466[167] = 0.0;
   out_3800934607722013466[168] = 0.0;
   out_3800934607722013466[169] = 0.0;
   out_3800934607722013466[170] = 0.0;
   out_3800934607722013466[171] = 1.0;
   out_3800934607722013466[172] = 0.0;
   out_3800934607722013466[173] = 0.0;
   out_3800934607722013466[174] = 0.0;
   out_3800934607722013466[175] = 0.0;
   out_3800934607722013466[176] = 0.0;
   out_3800934607722013466[177] = 0.0;
   out_3800934607722013466[178] = 0.0;
   out_3800934607722013466[179] = 0.0;
   out_3800934607722013466[180] = 0.0;
   out_3800934607722013466[181] = 0.0;
   out_3800934607722013466[182] = 0.0;
   out_3800934607722013466[183] = 0.0;
   out_3800934607722013466[184] = 0.0;
   out_3800934607722013466[185] = 0.0;
   out_3800934607722013466[186] = 0.0;
   out_3800934607722013466[187] = 0.0;
   out_3800934607722013466[188] = 0.0;
   out_3800934607722013466[189] = 0.0;
   out_3800934607722013466[190] = 1.0;
   out_3800934607722013466[191] = 0.0;
   out_3800934607722013466[192] = 0.0;
   out_3800934607722013466[193] = 0.0;
   out_3800934607722013466[194] = 0.0;
   out_3800934607722013466[195] = 0.0;
   out_3800934607722013466[196] = 0.0;
   out_3800934607722013466[197] = 0.0;
   out_3800934607722013466[198] = 0.0;
   out_3800934607722013466[199] = 0.0;
   out_3800934607722013466[200] = 0.0;
   out_3800934607722013466[201] = 0.0;
   out_3800934607722013466[202] = 0.0;
   out_3800934607722013466[203] = 0.0;
   out_3800934607722013466[204] = 0.0;
   out_3800934607722013466[205] = 0.0;
   out_3800934607722013466[206] = 0.0;
   out_3800934607722013466[207] = 0.0;
   out_3800934607722013466[208] = 0.0;
   out_3800934607722013466[209] = 1.0;
   out_3800934607722013466[210] = 0.0;
   out_3800934607722013466[211] = 0.0;
   out_3800934607722013466[212] = 0.0;
   out_3800934607722013466[213] = 0.0;
   out_3800934607722013466[214] = 0.0;
   out_3800934607722013466[215] = 0.0;
   out_3800934607722013466[216] = 0.0;
   out_3800934607722013466[217] = 0.0;
   out_3800934607722013466[218] = 0.0;
   out_3800934607722013466[219] = 0.0;
   out_3800934607722013466[220] = 0.0;
   out_3800934607722013466[221] = 0.0;
   out_3800934607722013466[222] = 0.0;
   out_3800934607722013466[223] = 0.0;
   out_3800934607722013466[224] = 0.0;
   out_3800934607722013466[225] = 0.0;
   out_3800934607722013466[226] = 0.0;
   out_3800934607722013466[227] = 0.0;
   out_3800934607722013466[228] = 1.0;
   out_3800934607722013466[229] = 0.0;
   out_3800934607722013466[230] = 0.0;
   out_3800934607722013466[231] = 0.0;
   out_3800934607722013466[232] = 0.0;
   out_3800934607722013466[233] = 0.0;
   out_3800934607722013466[234] = 0.0;
   out_3800934607722013466[235] = 0.0;
   out_3800934607722013466[236] = 0.0;
   out_3800934607722013466[237] = 0.0;
   out_3800934607722013466[238] = 0.0;
   out_3800934607722013466[239] = 0.0;
   out_3800934607722013466[240] = 0.0;
   out_3800934607722013466[241] = 0.0;
   out_3800934607722013466[242] = 0.0;
   out_3800934607722013466[243] = 0.0;
   out_3800934607722013466[244] = 0.0;
   out_3800934607722013466[245] = 0.0;
   out_3800934607722013466[246] = 0.0;
   out_3800934607722013466[247] = 1.0;
   out_3800934607722013466[248] = 0.0;
   out_3800934607722013466[249] = 0.0;
   out_3800934607722013466[250] = 0.0;
   out_3800934607722013466[251] = 0.0;
   out_3800934607722013466[252] = 0.0;
   out_3800934607722013466[253] = 0.0;
   out_3800934607722013466[254] = 0.0;
   out_3800934607722013466[255] = 0.0;
   out_3800934607722013466[256] = 0.0;
   out_3800934607722013466[257] = 0.0;
   out_3800934607722013466[258] = 0.0;
   out_3800934607722013466[259] = 0.0;
   out_3800934607722013466[260] = 0.0;
   out_3800934607722013466[261] = 0.0;
   out_3800934607722013466[262] = 0.0;
   out_3800934607722013466[263] = 0.0;
   out_3800934607722013466[264] = 0.0;
   out_3800934607722013466[265] = 0.0;
   out_3800934607722013466[266] = 1.0;
   out_3800934607722013466[267] = 0.0;
   out_3800934607722013466[268] = 0.0;
   out_3800934607722013466[269] = 0.0;
   out_3800934607722013466[270] = 0.0;
   out_3800934607722013466[271] = 0.0;
   out_3800934607722013466[272] = 0.0;
   out_3800934607722013466[273] = 0.0;
   out_3800934607722013466[274] = 0.0;
   out_3800934607722013466[275] = 0.0;
   out_3800934607722013466[276] = 0.0;
   out_3800934607722013466[277] = 0.0;
   out_3800934607722013466[278] = 0.0;
   out_3800934607722013466[279] = 0.0;
   out_3800934607722013466[280] = 0.0;
   out_3800934607722013466[281] = 0.0;
   out_3800934607722013466[282] = 0.0;
   out_3800934607722013466[283] = 0.0;
   out_3800934607722013466[284] = 0.0;
   out_3800934607722013466[285] = 1.0;
   out_3800934607722013466[286] = 0.0;
   out_3800934607722013466[287] = 0.0;
   out_3800934607722013466[288] = 0.0;
   out_3800934607722013466[289] = 0.0;
   out_3800934607722013466[290] = 0.0;
   out_3800934607722013466[291] = 0.0;
   out_3800934607722013466[292] = 0.0;
   out_3800934607722013466[293] = 0.0;
   out_3800934607722013466[294] = 0.0;
   out_3800934607722013466[295] = 0.0;
   out_3800934607722013466[296] = 0.0;
   out_3800934607722013466[297] = 0.0;
   out_3800934607722013466[298] = 0.0;
   out_3800934607722013466[299] = 0.0;
   out_3800934607722013466[300] = 0.0;
   out_3800934607722013466[301] = 0.0;
   out_3800934607722013466[302] = 0.0;
   out_3800934607722013466[303] = 0.0;
   out_3800934607722013466[304] = 1.0;
   out_3800934607722013466[305] = 0.0;
   out_3800934607722013466[306] = 0.0;
   out_3800934607722013466[307] = 0.0;
   out_3800934607722013466[308] = 0.0;
   out_3800934607722013466[309] = 0.0;
   out_3800934607722013466[310] = 0.0;
   out_3800934607722013466[311] = 0.0;
   out_3800934607722013466[312] = 0.0;
   out_3800934607722013466[313] = 0.0;
   out_3800934607722013466[314] = 0.0;
   out_3800934607722013466[315] = 0.0;
   out_3800934607722013466[316] = 0.0;
   out_3800934607722013466[317] = 0.0;
   out_3800934607722013466[318] = 0.0;
   out_3800934607722013466[319] = 0.0;
   out_3800934607722013466[320] = 0.0;
   out_3800934607722013466[321] = 0.0;
   out_3800934607722013466[322] = 0.0;
   out_3800934607722013466[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6652247469516692531) {
   out_6652247469516692531[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6652247469516692531[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6652247469516692531[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6652247469516692531[3] = dt*state[12] + state[3];
   out_6652247469516692531[4] = dt*state[13] + state[4];
   out_6652247469516692531[5] = dt*state[14] + state[5];
   out_6652247469516692531[6] = state[6];
   out_6652247469516692531[7] = state[7];
   out_6652247469516692531[8] = state[8];
   out_6652247469516692531[9] = state[9];
   out_6652247469516692531[10] = state[10];
   out_6652247469516692531[11] = state[11];
   out_6652247469516692531[12] = state[12];
   out_6652247469516692531[13] = state[13];
   out_6652247469516692531[14] = state[14];
   out_6652247469516692531[15] = state[15];
   out_6652247469516692531[16] = state[16];
   out_6652247469516692531[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8011247107029651568) {
   out_8011247107029651568[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8011247107029651568[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8011247107029651568[2] = 0;
   out_8011247107029651568[3] = 0;
   out_8011247107029651568[4] = 0;
   out_8011247107029651568[5] = 0;
   out_8011247107029651568[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8011247107029651568[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8011247107029651568[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8011247107029651568[9] = 0;
   out_8011247107029651568[10] = 0;
   out_8011247107029651568[11] = 0;
   out_8011247107029651568[12] = 0;
   out_8011247107029651568[13] = 0;
   out_8011247107029651568[14] = 0;
   out_8011247107029651568[15] = 0;
   out_8011247107029651568[16] = 0;
   out_8011247107029651568[17] = 0;
   out_8011247107029651568[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8011247107029651568[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8011247107029651568[20] = 0;
   out_8011247107029651568[21] = 0;
   out_8011247107029651568[22] = 0;
   out_8011247107029651568[23] = 0;
   out_8011247107029651568[24] = 0;
   out_8011247107029651568[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8011247107029651568[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8011247107029651568[27] = 0;
   out_8011247107029651568[28] = 0;
   out_8011247107029651568[29] = 0;
   out_8011247107029651568[30] = 0;
   out_8011247107029651568[31] = 0;
   out_8011247107029651568[32] = 0;
   out_8011247107029651568[33] = 0;
   out_8011247107029651568[34] = 0;
   out_8011247107029651568[35] = 0;
   out_8011247107029651568[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8011247107029651568[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8011247107029651568[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8011247107029651568[39] = 0;
   out_8011247107029651568[40] = 0;
   out_8011247107029651568[41] = 0;
   out_8011247107029651568[42] = 0;
   out_8011247107029651568[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8011247107029651568[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8011247107029651568[45] = 0;
   out_8011247107029651568[46] = 0;
   out_8011247107029651568[47] = 0;
   out_8011247107029651568[48] = 0;
   out_8011247107029651568[49] = 0;
   out_8011247107029651568[50] = 0;
   out_8011247107029651568[51] = 0;
   out_8011247107029651568[52] = 0;
   out_8011247107029651568[53] = 0;
   out_8011247107029651568[54] = 0;
   out_8011247107029651568[55] = 0;
   out_8011247107029651568[56] = 0;
   out_8011247107029651568[57] = 1;
   out_8011247107029651568[58] = 0;
   out_8011247107029651568[59] = 0;
   out_8011247107029651568[60] = 0;
   out_8011247107029651568[61] = 0;
   out_8011247107029651568[62] = 0;
   out_8011247107029651568[63] = 0;
   out_8011247107029651568[64] = 0;
   out_8011247107029651568[65] = 0;
   out_8011247107029651568[66] = dt;
   out_8011247107029651568[67] = 0;
   out_8011247107029651568[68] = 0;
   out_8011247107029651568[69] = 0;
   out_8011247107029651568[70] = 0;
   out_8011247107029651568[71] = 0;
   out_8011247107029651568[72] = 0;
   out_8011247107029651568[73] = 0;
   out_8011247107029651568[74] = 0;
   out_8011247107029651568[75] = 0;
   out_8011247107029651568[76] = 1;
   out_8011247107029651568[77] = 0;
   out_8011247107029651568[78] = 0;
   out_8011247107029651568[79] = 0;
   out_8011247107029651568[80] = 0;
   out_8011247107029651568[81] = 0;
   out_8011247107029651568[82] = 0;
   out_8011247107029651568[83] = 0;
   out_8011247107029651568[84] = 0;
   out_8011247107029651568[85] = dt;
   out_8011247107029651568[86] = 0;
   out_8011247107029651568[87] = 0;
   out_8011247107029651568[88] = 0;
   out_8011247107029651568[89] = 0;
   out_8011247107029651568[90] = 0;
   out_8011247107029651568[91] = 0;
   out_8011247107029651568[92] = 0;
   out_8011247107029651568[93] = 0;
   out_8011247107029651568[94] = 0;
   out_8011247107029651568[95] = 1;
   out_8011247107029651568[96] = 0;
   out_8011247107029651568[97] = 0;
   out_8011247107029651568[98] = 0;
   out_8011247107029651568[99] = 0;
   out_8011247107029651568[100] = 0;
   out_8011247107029651568[101] = 0;
   out_8011247107029651568[102] = 0;
   out_8011247107029651568[103] = 0;
   out_8011247107029651568[104] = dt;
   out_8011247107029651568[105] = 0;
   out_8011247107029651568[106] = 0;
   out_8011247107029651568[107] = 0;
   out_8011247107029651568[108] = 0;
   out_8011247107029651568[109] = 0;
   out_8011247107029651568[110] = 0;
   out_8011247107029651568[111] = 0;
   out_8011247107029651568[112] = 0;
   out_8011247107029651568[113] = 0;
   out_8011247107029651568[114] = 1;
   out_8011247107029651568[115] = 0;
   out_8011247107029651568[116] = 0;
   out_8011247107029651568[117] = 0;
   out_8011247107029651568[118] = 0;
   out_8011247107029651568[119] = 0;
   out_8011247107029651568[120] = 0;
   out_8011247107029651568[121] = 0;
   out_8011247107029651568[122] = 0;
   out_8011247107029651568[123] = 0;
   out_8011247107029651568[124] = 0;
   out_8011247107029651568[125] = 0;
   out_8011247107029651568[126] = 0;
   out_8011247107029651568[127] = 0;
   out_8011247107029651568[128] = 0;
   out_8011247107029651568[129] = 0;
   out_8011247107029651568[130] = 0;
   out_8011247107029651568[131] = 0;
   out_8011247107029651568[132] = 0;
   out_8011247107029651568[133] = 1;
   out_8011247107029651568[134] = 0;
   out_8011247107029651568[135] = 0;
   out_8011247107029651568[136] = 0;
   out_8011247107029651568[137] = 0;
   out_8011247107029651568[138] = 0;
   out_8011247107029651568[139] = 0;
   out_8011247107029651568[140] = 0;
   out_8011247107029651568[141] = 0;
   out_8011247107029651568[142] = 0;
   out_8011247107029651568[143] = 0;
   out_8011247107029651568[144] = 0;
   out_8011247107029651568[145] = 0;
   out_8011247107029651568[146] = 0;
   out_8011247107029651568[147] = 0;
   out_8011247107029651568[148] = 0;
   out_8011247107029651568[149] = 0;
   out_8011247107029651568[150] = 0;
   out_8011247107029651568[151] = 0;
   out_8011247107029651568[152] = 1;
   out_8011247107029651568[153] = 0;
   out_8011247107029651568[154] = 0;
   out_8011247107029651568[155] = 0;
   out_8011247107029651568[156] = 0;
   out_8011247107029651568[157] = 0;
   out_8011247107029651568[158] = 0;
   out_8011247107029651568[159] = 0;
   out_8011247107029651568[160] = 0;
   out_8011247107029651568[161] = 0;
   out_8011247107029651568[162] = 0;
   out_8011247107029651568[163] = 0;
   out_8011247107029651568[164] = 0;
   out_8011247107029651568[165] = 0;
   out_8011247107029651568[166] = 0;
   out_8011247107029651568[167] = 0;
   out_8011247107029651568[168] = 0;
   out_8011247107029651568[169] = 0;
   out_8011247107029651568[170] = 0;
   out_8011247107029651568[171] = 1;
   out_8011247107029651568[172] = 0;
   out_8011247107029651568[173] = 0;
   out_8011247107029651568[174] = 0;
   out_8011247107029651568[175] = 0;
   out_8011247107029651568[176] = 0;
   out_8011247107029651568[177] = 0;
   out_8011247107029651568[178] = 0;
   out_8011247107029651568[179] = 0;
   out_8011247107029651568[180] = 0;
   out_8011247107029651568[181] = 0;
   out_8011247107029651568[182] = 0;
   out_8011247107029651568[183] = 0;
   out_8011247107029651568[184] = 0;
   out_8011247107029651568[185] = 0;
   out_8011247107029651568[186] = 0;
   out_8011247107029651568[187] = 0;
   out_8011247107029651568[188] = 0;
   out_8011247107029651568[189] = 0;
   out_8011247107029651568[190] = 1;
   out_8011247107029651568[191] = 0;
   out_8011247107029651568[192] = 0;
   out_8011247107029651568[193] = 0;
   out_8011247107029651568[194] = 0;
   out_8011247107029651568[195] = 0;
   out_8011247107029651568[196] = 0;
   out_8011247107029651568[197] = 0;
   out_8011247107029651568[198] = 0;
   out_8011247107029651568[199] = 0;
   out_8011247107029651568[200] = 0;
   out_8011247107029651568[201] = 0;
   out_8011247107029651568[202] = 0;
   out_8011247107029651568[203] = 0;
   out_8011247107029651568[204] = 0;
   out_8011247107029651568[205] = 0;
   out_8011247107029651568[206] = 0;
   out_8011247107029651568[207] = 0;
   out_8011247107029651568[208] = 0;
   out_8011247107029651568[209] = 1;
   out_8011247107029651568[210] = 0;
   out_8011247107029651568[211] = 0;
   out_8011247107029651568[212] = 0;
   out_8011247107029651568[213] = 0;
   out_8011247107029651568[214] = 0;
   out_8011247107029651568[215] = 0;
   out_8011247107029651568[216] = 0;
   out_8011247107029651568[217] = 0;
   out_8011247107029651568[218] = 0;
   out_8011247107029651568[219] = 0;
   out_8011247107029651568[220] = 0;
   out_8011247107029651568[221] = 0;
   out_8011247107029651568[222] = 0;
   out_8011247107029651568[223] = 0;
   out_8011247107029651568[224] = 0;
   out_8011247107029651568[225] = 0;
   out_8011247107029651568[226] = 0;
   out_8011247107029651568[227] = 0;
   out_8011247107029651568[228] = 1;
   out_8011247107029651568[229] = 0;
   out_8011247107029651568[230] = 0;
   out_8011247107029651568[231] = 0;
   out_8011247107029651568[232] = 0;
   out_8011247107029651568[233] = 0;
   out_8011247107029651568[234] = 0;
   out_8011247107029651568[235] = 0;
   out_8011247107029651568[236] = 0;
   out_8011247107029651568[237] = 0;
   out_8011247107029651568[238] = 0;
   out_8011247107029651568[239] = 0;
   out_8011247107029651568[240] = 0;
   out_8011247107029651568[241] = 0;
   out_8011247107029651568[242] = 0;
   out_8011247107029651568[243] = 0;
   out_8011247107029651568[244] = 0;
   out_8011247107029651568[245] = 0;
   out_8011247107029651568[246] = 0;
   out_8011247107029651568[247] = 1;
   out_8011247107029651568[248] = 0;
   out_8011247107029651568[249] = 0;
   out_8011247107029651568[250] = 0;
   out_8011247107029651568[251] = 0;
   out_8011247107029651568[252] = 0;
   out_8011247107029651568[253] = 0;
   out_8011247107029651568[254] = 0;
   out_8011247107029651568[255] = 0;
   out_8011247107029651568[256] = 0;
   out_8011247107029651568[257] = 0;
   out_8011247107029651568[258] = 0;
   out_8011247107029651568[259] = 0;
   out_8011247107029651568[260] = 0;
   out_8011247107029651568[261] = 0;
   out_8011247107029651568[262] = 0;
   out_8011247107029651568[263] = 0;
   out_8011247107029651568[264] = 0;
   out_8011247107029651568[265] = 0;
   out_8011247107029651568[266] = 1;
   out_8011247107029651568[267] = 0;
   out_8011247107029651568[268] = 0;
   out_8011247107029651568[269] = 0;
   out_8011247107029651568[270] = 0;
   out_8011247107029651568[271] = 0;
   out_8011247107029651568[272] = 0;
   out_8011247107029651568[273] = 0;
   out_8011247107029651568[274] = 0;
   out_8011247107029651568[275] = 0;
   out_8011247107029651568[276] = 0;
   out_8011247107029651568[277] = 0;
   out_8011247107029651568[278] = 0;
   out_8011247107029651568[279] = 0;
   out_8011247107029651568[280] = 0;
   out_8011247107029651568[281] = 0;
   out_8011247107029651568[282] = 0;
   out_8011247107029651568[283] = 0;
   out_8011247107029651568[284] = 0;
   out_8011247107029651568[285] = 1;
   out_8011247107029651568[286] = 0;
   out_8011247107029651568[287] = 0;
   out_8011247107029651568[288] = 0;
   out_8011247107029651568[289] = 0;
   out_8011247107029651568[290] = 0;
   out_8011247107029651568[291] = 0;
   out_8011247107029651568[292] = 0;
   out_8011247107029651568[293] = 0;
   out_8011247107029651568[294] = 0;
   out_8011247107029651568[295] = 0;
   out_8011247107029651568[296] = 0;
   out_8011247107029651568[297] = 0;
   out_8011247107029651568[298] = 0;
   out_8011247107029651568[299] = 0;
   out_8011247107029651568[300] = 0;
   out_8011247107029651568[301] = 0;
   out_8011247107029651568[302] = 0;
   out_8011247107029651568[303] = 0;
   out_8011247107029651568[304] = 1;
   out_8011247107029651568[305] = 0;
   out_8011247107029651568[306] = 0;
   out_8011247107029651568[307] = 0;
   out_8011247107029651568[308] = 0;
   out_8011247107029651568[309] = 0;
   out_8011247107029651568[310] = 0;
   out_8011247107029651568[311] = 0;
   out_8011247107029651568[312] = 0;
   out_8011247107029651568[313] = 0;
   out_8011247107029651568[314] = 0;
   out_8011247107029651568[315] = 0;
   out_8011247107029651568[316] = 0;
   out_8011247107029651568[317] = 0;
   out_8011247107029651568[318] = 0;
   out_8011247107029651568[319] = 0;
   out_8011247107029651568[320] = 0;
   out_8011247107029651568[321] = 0;
   out_8011247107029651568[322] = 0;
   out_8011247107029651568[323] = 1;
}
void h_4(double *state, double *unused, double *out_1414268185846324142) {
   out_1414268185846324142[0] = state[6] + state[9];
   out_1414268185846324142[1] = state[7] + state[10];
   out_1414268185846324142[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5620633333628310327) {
   out_5620633333628310327[0] = 0;
   out_5620633333628310327[1] = 0;
   out_5620633333628310327[2] = 0;
   out_5620633333628310327[3] = 0;
   out_5620633333628310327[4] = 0;
   out_5620633333628310327[5] = 0;
   out_5620633333628310327[6] = 1;
   out_5620633333628310327[7] = 0;
   out_5620633333628310327[8] = 0;
   out_5620633333628310327[9] = 1;
   out_5620633333628310327[10] = 0;
   out_5620633333628310327[11] = 0;
   out_5620633333628310327[12] = 0;
   out_5620633333628310327[13] = 0;
   out_5620633333628310327[14] = 0;
   out_5620633333628310327[15] = 0;
   out_5620633333628310327[16] = 0;
   out_5620633333628310327[17] = 0;
   out_5620633333628310327[18] = 0;
   out_5620633333628310327[19] = 0;
   out_5620633333628310327[20] = 0;
   out_5620633333628310327[21] = 0;
   out_5620633333628310327[22] = 0;
   out_5620633333628310327[23] = 0;
   out_5620633333628310327[24] = 0;
   out_5620633333628310327[25] = 1;
   out_5620633333628310327[26] = 0;
   out_5620633333628310327[27] = 0;
   out_5620633333628310327[28] = 1;
   out_5620633333628310327[29] = 0;
   out_5620633333628310327[30] = 0;
   out_5620633333628310327[31] = 0;
   out_5620633333628310327[32] = 0;
   out_5620633333628310327[33] = 0;
   out_5620633333628310327[34] = 0;
   out_5620633333628310327[35] = 0;
   out_5620633333628310327[36] = 0;
   out_5620633333628310327[37] = 0;
   out_5620633333628310327[38] = 0;
   out_5620633333628310327[39] = 0;
   out_5620633333628310327[40] = 0;
   out_5620633333628310327[41] = 0;
   out_5620633333628310327[42] = 0;
   out_5620633333628310327[43] = 0;
   out_5620633333628310327[44] = 1;
   out_5620633333628310327[45] = 0;
   out_5620633333628310327[46] = 0;
   out_5620633333628310327[47] = 1;
   out_5620633333628310327[48] = 0;
   out_5620633333628310327[49] = 0;
   out_5620633333628310327[50] = 0;
   out_5620633333628310327[51] = 0;
   out_5620633333628310327[52] = 0;
   out_5620633333628310327[53] = 0;
}
void h_10(double *state, double *unused, double *out_485138144046796067) {
   out_485138144046796067[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_485138144046796067[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_485138144046796067[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5435004367830975165) {
   out_5435004367830975165[0] = 0;
   out_5435004367830975165[1] = 9.8100000000000005*cos(state[1]);
   out_5435004367830975165[2] = 0;
   out_5435004367830975165[3] = 0;
   out_5435004367830975165[4] = -state[8];
   out_5435004367830975165[5] = state[7];
   out_5435004367830975165[6] = 0;
   out_5435004367830975165[7] = state[5];
   out_5435004367830975165[8] = -state[4];
   out_5435004367830975165[9] = 0;
   out_5435004367830975165[10] = 0;
   out_5435004367830975165[11] = 0;
   out_5435004367830975165[12] = 1;
   out_5435004367830975165[13] = 0;
   out_5435004367830975165[14] = 0;
   out_5435004367830975165[15] = 1;
   out_5435004367830975165[16] = 0;
   out_5435004367830975165[17] = 0;
   out_5435004367830975165[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5435004367830975165[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5435004367830975165[20] = 0;
   out_5435004367830975165[21] = state[8];
   out_5435004367830975165[22] = 0;
   out_5435004367830975165[23] = -state[6];
   out_5435004367830975165[24] = -state[5];
   out_5435004367830975165[25] = 0;
   out_5435004367830975165[26] = state[3];
   out_5435004367830975165[27] = 0;
   out_5435004367830975165[28] = 0;
   out_5435004367830975165[29] = 0;
   out_5435004367830975165[30] = 0;
   out_5435004367830975165[31] = 1;
   out_5435004367830975165[32] = 0;
   out_5435004367830975165[33] = 0;
   out_5435004367830975165[34] = 1;
   out_5435004367830975165[35] = 0;
   out_5435004367830975165[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5435004367830975165[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5435004367830975165[38] = 0;
   out_5435004367830975165[39] = -state[7];
   out_5435004367830975165[40] = state[6];
   out_5435004367830975165[41] = 0;
   out_5435004367830975165[42] = state[4];
   out_5435004367830975165[43] = -state[3];
   out_5435004367830975165[44] = 0;
   out_5435004367830975165[45] = 0;
   out_5435004367830975165[46] = 0;
   out_5435004367830975165[47] = 0;
   out_5435004367830975165[48] = 0;
   out_5435004367830975165[49] = 0;
   out_5435004367830975165[50] = 1;
   out_5435004367830975165[51] = 0;
   out_5435004367830975165[52] = 0;
   out_5435004367830975165[53] = 1;
}
void h_13(double *state, double *unused, double *out_5970031784927357775) {
   out_5970031784927357775[0] = state[3];
   out_5970031784927357775[1] = state[4];
   out_5970031784927357775[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2408359508295977526) {
   out_2408359508295977526[0] = 0;
   out_2408359508295977526[1] = 0;
   out_2408359508295977526[2] = 0;
   out_2408359508295977526[3] = 1;
   out_2408359508295977526[4] = 0;
   out_2408359508295977526[5] = 0;
   out_2408359508295977526[6] = 0;
   out_2408359508295977526[7] = 0;
   out_2408359508295977526[8] = 0;
   out_2408359508295977526[9] = 0;
   out_2408359508295977526[10] = 0;
   out_2408359508295977526[11] = 0;
   out_2408359508295977526[12] = 0;
   out_2408359508295977526[13] = 0;
   out_2408359508295977526[14] = 0;
   out_2408359508295977526[15] = 0;
   out_2408359508295977526[16] = 0;
   out_2408359508295977526[17] = 0;
   out_2408359508295977526[18] = 0;
   out_2408359508295977526[19] = 0;
   out_2408359508295977526[20] = 0;
   out_2408359508295977526[21] = 0;
   out_2408359508295977526[22] = 1;
   out_2408359508295977526[23] = 0;
   out_2408359508295977526[24] = 0;
   out_2408359508295977526[25] = 0;
   out_2408359508295977526[26] = 0;
   out_2408359508295977526[27] = 0;
   out_2408359508295977526[28] = 0;
   out_2408359508295977526[29] = 0;
   out_2408359508295977526[30] = 0;
   out_2408359508295977526[31] = 0;
   out_2408359508295977526[32] = 0;
   out_2408359508295977526[33] = 0;
   out_2408359508295977526[34] = 0;
   out_2408359508295977526[35] = 0;
   out_2408359508295977526[36] = 0;
   out_2408359508295977526[37] = 0;
   out_2408359508295977526[38] = 0;
   out_2408359508295977526[39] = 0;
   out_2408359508295977526[40] = 0;
   out_2408359508295977526[41] = 1;
   out_2408359508295977526[42] = 0;
   out_2408359508295977526[43] = 0;
   out_2408359508295977526[44] = 0;
   out_2408359508295977526[45] = 0;
   out_2408359508295977526[46] = 0;
   out_2408359508295977526[47] = 0;
   out_2408359508295977526[48] = 0;
   out_2408359508295977526[49] = 0;
   out_2408359508295977526[50] = 0;
   out_2408359508295977526[51] = 0;
   out_2408359508295977526[52] = 0;
   out_2408359508295977526[53] = 0;
}
void h_14(double *state, double *unused, double *out_2427394029087566377) {
   out_2427394029087566377[0] = state[6];
   out_2427394029087566377[1] = state[7];
   out_2427394029087566377[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1657392477288825798) {
   out_1657392477288825798[0] = 0;
   out_1657392477288825798[1] = 0;
   out_1657392477288825798[2] = 0;
   out_1657392477288825798[3] = 0;
   out_1657392477288825798[4] = 0;
   out_1657392477288825798[5] = 0;
   out_1657392477288825798[6] = 1;
   out_1657392477288825798[7] = 0;
   out_1657392477288825798[8] = 0;
   out_1657392477288825798[9] = 0;
   out_1657392477288825798[10] = 0;
   out_1657392477288825798[11] = 0;
   out_1657392477288825798[12] = 0;
   out_1657392477288825798[13] = 0;
   out_1657392477288825798[14] = 0;
   out_1657392477288825798[15] = 0;
   out_1657392477288825798[16] = 0;
   out_1657392477288825798[17] = 0;
   out_1657392477288825798[18] = 0;
   out_1657392477288825798[19] = 0;
   out_1657392477288825798[20] = 0;
   out_1657392477288825798[21] = 0;
   out_1657392477288825798[22] = 0;
   out_1657392477288825798[23] = 0;
   out_1657392477288825798[24] = 0;
   out_1657392477288825798[25] = 1;
   out_1657392477288825798[26] = 0;
   out_1657392477288825798[27] = 0;
   out_1657392477288825798[28] = 0;
   out_1657392477288825798[29] = 0;
   out_1657392477288825798[30] = 0;
   out_1657392477288825798[31] = 0;
   out_1657392477288825798[32] = 0;
   out_1657392477288825798[33] = 0;
   out_1657392477288825798[34] = 0;
   out_1657392477288825798[35] = 0;
   out_1657392477288825798[36] = 0;
   out_1657392477288825798[37] = 0;
   out_1657392477288825798[38] = 0;
   out_1657392477288825798[39] = 0;
   out_1657392477288825798[40] = 0;
   out_1657392477288825798[41] = 0;
   out_1657392477288825798[42] = 0;
   out_1657392477288825798[43] = 0;
   out_1657392477288825798[44] = 1;
   out_1657392477288825798[45] = 0;
   out_1657392477288825798[46] = 0;
   out_1657392477288825798[47] = 0;
   out_1657392477288825798[48] = 0;
   out_1657392477288825798[49] = 0;
   out_1657392477288825798[50] = 0;
   out_1657392477288825798[51] = 0;
   out_1657392477288825798[52] = 0;
   out_1657392477288825798[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8769047576014597915) {
  err_fun(nom_x, delta_x, out_8769047576014597915);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6606884682512325288) {
  inv_err_fun(nom_x, true_x, out_6606884682512325288);
}
void pose_H_mod_fun(double *state, double *out_3800934607722013466) {
  H_mod_fun(state, out_3800934607722013466);
}
void pose_f_fun(double *state, double dt, double *out_6652247469516692531) {
  f_fun(state,  dt, out_6652247469516692531);
}
void pose_F_fun(double *state, double dt, double *out_8011247107029651568) {
  F_fun(state,  dt, out_8011247107029651568);
}
void pose_h_4(double *state, double *unused, double *out_1414268185846324142) {
  h_4(state, unused, out_1414268185846324142);
}
void pose_H_4(double *state, double *unused, double *out_5620633333628310327) {
  H_4(state, unused, out_5620633333628310327);
}
void pose_h_10(double *state, double *unused, double *out_485138144046796067) {
  h_10(state, unused, out_485138144046796067);
}
void pose_H_10(double *state, double *unused, double *out_5435004367830975165) {
  H_10(state, unused, out_5435004367830975165);
}
void pose_h_13(double *state, double *unused, double *out_5970031784927357775) {
  h_13(state, unused, out_5970031784927357775);
}
void pose_H_13(double *state, double *unused, double *out_2408359508295977526) {
  H_13(state, unused, out_2408359508295977526);
}
void pose_h_14(double *state, double *unused, double *out_2427394029087566377) {
  h_14(state, unused, out_2427394029087566377);
}
void pose_H_14(double *state, double *unused, double *out_1657392477288825798) {
  H_14(state, unused, out_1657392477288825798);
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
