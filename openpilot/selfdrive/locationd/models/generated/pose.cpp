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
void err_fun(double *nom_x, double *delta_x, double *out_1314885097679334068) {
   out_1314885097679334068[0] = delta_x[0] + nom_x[0];
   out_1314885097679334068[1] = delta_x[1] + nom_x[1];
   out_1314885097679334068[2] = delta_x[2] + nom_x[2];
   out_1314885097679334068[3] = delta_x[3] + nom_x[3];
   out_1314885097679334068[4] = delta_x[4] + nom_x[4];
   out_1314885097679334068[5] = delta_x[5] + nom_x[5];
   out_1314885097679334068[6] = delta_x[6] + nom_x[6];
   out_1314885097679334068[7] = delta_x[7] + nom_x[7];
   out_1314885097679334068[8] = delta_x[8] + nom_x[8];
   out_1314885097679334068[9] = delta_x[9] + nom_x[9];
   out_1314885097679334068[10] = delta_x[10] + nom_x[10];
   out_1314885097679334068[11] = delta_x[11] + nom_x[11];
   out_1314885097679334068[12] = delta_x[12] + nom_x[12];
   out_1314885097679334068[13] = delta_x[13] + nom_x[13];
   out_1314885097679334068[14] = delta_x[14] + nom_x[14];
   out_1314885097679334068[15] = delta_x[15] + nom_x[15];
   out_1314885097679334068[16] = delta_x[16] + nom_x[16];
   out_1314885097679334068[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2457185809051772100) {
   out_2457185809051772100[0] = -nom_x[0] + true_x[0];
   out_2457185809051772100[1] = -nom_x[1] + true_x[1];
   out_2457185809051772100[2] = -nom_x[2] + true_x[2];
   out_2457185809051772100[3] = -nom_x[3] + true_x[3];
   out_2457185809051772100[4] = -nom_x[4] + true_x[4];
   out_2457185809051772100[5] = -nom_x[5] + true_x[5];
   out_2457185809051772100[6] = -nom_x[6] + true_x[6];
   out_2457185809051772100[7] = -nom_x[7] + true_x[7];
   out_2457185809051772100[8] = -nom_x[8] + true_x[8];
   out_2457185809051772100[9] = -nom_x[9] + true_x[9];
   out_2457185809051772100[10] = -nom_x[10] + true_x[10];
   out_2457185809051772100[11] = -nom_x[11] + true_x[11];
   out_2457185809051772100[12] = -nom_x[12] + true_x[12];
   out_2457185809051772100[13] = -nom_x[13] + true_x[13];
   out_2457185809051772100[14] = -nom_x[14] + true_x[14];
   out_2457185809051772100[15] = -nom_x[15] + true_x[15];
   out_2457185809051772100[16] = -nom_x[16] + true_x[16];
   out_2457185809051772100[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2842365525503581863) {
   out_2842365525503581863[0] = 1.0;
   out_2842365525503581863[1] = 0.0;
   out_2842365525503581863[2] = 0.0;
   out_2842365525503581863[3] = 0.0;
   out_2842365525503581863[4] = 0.0;
   out_2842365525503581863[5] = 0.0;
   out_2842365525503581863[6] = 0.0;
   out_2842365525503581863[7] = 0.0;
   out_2842365525503581863[8] = 0.0;
   out_2842365525503581863[9] = 0.0;
   out_2842365525503581863[10] = 0.0;
   out_2842365525503581863[11] = 0.0;
   out_2842365525503581863[12] = 0.0;
   out_2842365525503581863[13] = 0.0;
   out_2842365525503581863[14] = 0.0;
   out_2842365525503581863[15] = 0.0;
   out_2842365525503581863[16] = 0.0;
   out_2842365525503581863[17] = 0.0;
   out_2842365525503581863[18] = 0.0;
   out_2842365525503581863[19] = 1.0;
   out_2842365525503581863[20] = 0.0;
   out_2842365525503581863[21] = 0.0;
   out_2842365525503581863[22] = 0.0;
   out_2842365525503581863[23] = 0.0;
   out_2842365525503581863[24] = 0.0;
   out_2842365525503581863[25] = 0.0;
   out_2842365525503581863[26] = 0.0;
   out_2842365525503581863[27] = 0.0;
   out_2842365525503581863[28] = 0.0;
   out_2842365525503581863[29] = 0.0;
   out_2842365525503581863[30] = 0.0;
   out_2842365525503581863[31] = 0.0;
   out_2842365525503581863[32] = 0.0;
   out_2842365525503581863[33] = 0.0;
   out_2842365525503581863[34] = 0.0;
   out_2842365525503581863[35] = 0.0;
   out_2842365525503581863[36] = 0.0;
   out_2842365525503581863[37] = 0.0;
   out_2842365525503581863[38] = 1.0;
   out_2842365525503581863[39] = 0.0;
   out_2842365525503581863[40] = 0.0;
   out_2842365525503581863[41] = 0.0;
   out_2842365525503581863[42] = 0.0;
   out_2842365525503581863[43] = 0.0;
   out_2842365525503581863[44] = 0.0;
   out_2842365525503581863[45] = 0.0;
   out_2842365525503581863[46] = 0.0;
   out_2842365525503581863[47] = 0.0;
   out_2842365525503581863[48] = 0.0;
   out_2842365525503581863[49] = 0.0;
   out_2842365525503581863[50] = 0.0;
   out_2842365525503581863[51] = 0.0;
   out_2842365525503581863[52] = 0.0;
   out_2842365525503581863[53] = 0.0;
   out_2842365525503581863[54] = 0.0;
   out_2842365525503581863[55] = 0.0;
   out_2842365525503581863[56] = 0.0;
   out_2842365525503581863[57] = 1.0;
   out_2842365525503581863[58] = 0.0;
   out_2842365525503581863[59] = 0.0;
   out_2842365525503581863[60] = 0.0;
   out_2842365525503581863[61] = 0.0;
   out_2842365525503581863[62] = 0.0;
   out_2842365525503581863[63] = 0.0;
   out_2842365525503581863[64] = 0.0;
   out_2842365525503581863[65] = 0.0;
   out_2842365525503581863[66] = 0.0;
   out_2842365525503581863[67] = 0.0;
   out_2842365525503581863[68] = 0.0;
   out_2842365525503581863[69] = 0.0;
   out_2842365525503581863[70] = 0.0;
   out_2842365525503581863[71] = 0.0;
   out_2842365525503581863[72] = 0.0;
   out_2842365525503581863[73] = 0.0;
   out_2842365525503581863[74] = 0.0;
   out_2842365525503581863[75] = 0.0;
   out_2842365525503581863[76] = 1.0;
   out_2842365525503581863[77] = 0.0;
   out_2842365525503581863[78] = 0.0;
   out_2842365525503581863[79] = 0.0;
   out_2842365525503581863[80] = 0.0;
   out_2842365525503581863[81] = 0.0;
   out_2842365525503581863[82] = 0.0;
   out_2842365525503581863[83] = 0.0;
   out_2842365525503581863[84] = 0.0;
   out_2842365525503581863[85] = 0.0;
   out_2842365525503581863[86] = 0.0;
   out_2842365525503581863[87] = 0.0;
   out_2842365525503581863[88] = 0.0;
   out_2842365525503581863[89] = 0.0;
   out_2842365525503581863[90] = 0.0;
   out_2842365525503581863[91] = 0.0;
   out_2842365525503581863[92] = 0.0;
   out_2842365525503581863[93] = 0.0;
   out_2842365525503581863[94] = 0.0;
   out_2842365525503581863[95] = 1.0;
   out_2842365525503581863[96] = 0.0;
   out_2842365525503581863[97] = 0.0;
   out_2842365525503581863[98] = 0.0;
   out_2842365525503581863[99] = 0.0;
   out_2842365525503581863[100] = 0.0;
   out_2842365525503581863[101] = 0.0;
   out_2842365525503581863[102] = 0.0;
   out_2842365525503581863[103] = 0.0;
   out_2842365525503581863[104] = 0.0;
   out_2842365525503581863[105] = 0.0;
   out_2842365525503581863[106] = 0.0;
   out_2842365525503581863[107] = 0.0;
   out_2842365525503581863[108] = 0.0;
   out_2842365525503581863[109] = 0.0;
   out_2842365525503581863[110] = 0.0;
   out_2842365525503581863[111] = 0.0;
   out_2842365525503581863[112] = 0.0;
   out_2842365525503581863[113] = 0.0;
   out_2842365525503581863[114] = 1.0;
   out_2842365525503581863[115] = 0.0;
   out_2842365525503581863[116] = 0.0;
   out_2842365525503581863[117] = 0.0;
   out_2842365525503581863[118] = 0.0;
   out_2842365525503581863[119] = 0.0;
   out_2842365525503581863[120] = 0.0;
   out_2842365525503581863[121] = 0.0;
   out_2842365525503581863[122] = 0.0;
   out_2842365525503581863[123] = 0.0;
   out_2842365525503581863[124] = 0.0;
   out_2842365525503581863[125] = 0.0;
   out_2842365525503581863[126] = 0.0;
   out_2842365525503581863[127] = 0.0;
   out_2842365525503581863[128] = 0.0;
   out_2842365525503581863[129] = 0.0;
   out_2842365525503581863[130] = 0.0;
   out_2842365525503581863[131] = 0.0;
   out_2842365525503581863[132] = 0.0;
   out_2842365525503581863[133] = 1.0;
   out_2842365525503581863[134] = 0.0;
   out_2842365525503581863[135] = 0.0;
   out_2842365525503581863[136] = 0.0;
   out_2842365525503581863[137] = 0.0;
   out_2842365525503581863[138] = 0.0;
   out_2842365525503581863[139] = 0.0;
   out_2842365525503581863[140] = 0.0;
   out_2842365525503581863[141] = 0.0;
   out_2842365525503581863[142] = 0.0;
   out_2842365525503581863[143] = 0.0;
   out_2842365525503581863[144] = 0.0;
   out_2842365525503581863[145] = 0.0;
   out_2842365525503581863[146] = 0.0;
   out_2842365525503581863[147] = 0.0;
   out_2842365525503581863[148] = 0.0;
   out_2842365525503581863[149] = 0.0;
   out_2842365525503581863[150] = 0.0;
   out_2842365525503581863[151] = 0.0;
   out_2842365525503581863[152] = 1.0;
   out_2842365525503581863[153] = 0.0;
   out_2842365525503581863[154] = 0.0;
   out_2842365525503581863[155] = 0.0;
   out_2842365525503581863[156] = 0.0;
   out_2842365525503581863[157] = 0.0;
   out_2842365525503581863[158] = 0.0;
   out_2842365525503581863[159] = 0.0;
   out_2842365525503581863[160] = 0.0;
   out_2842365525503581863[161] = 0.0;
   out_2842365525503581863[162] = 0.0;
   out_2842365525503581863[163] = 0.0;
   out_2842365525503581863[164] = 0.0;
   out_2842365525503581863[165] = 0.0;
   out_2842365525503581863[166] = 0.0;
   out_2842365525503581863[167] = 0.0;
   out_2842365525503581863[168] = 0.0;
   out_2842365525503581863[169] = 0.0;
   out_2842365525503581863[170] = 0.0;
   out_2842365525503581863[171] = 1.0;
   out_2842365525503581863[172] = 0.0;
   out_2842365525503581863[173] = 0.0;
   out_2842365525503581863[174] = 0.0;
   out_2842365525503581863[175] = 0.0;
   out_2842365525503581863[176] = 0.0;
   out_2842365525503581863[177] = 0.0;
   out_2842365525503581863[178] = 0.0;
   out_2842365525503581863[179] = 0.0;
   out_2842365525503581863[180] = 0.0;
   out_2842365525503581863[181] = 0.0;
   out_2842365525503581863[182] = 0.0;
   out_2842365525503581863[183] = 0.0;
   out_2842365525503581863[184] = 0.0;
   out_2842365525503581863[185] = 0.0;
   out_2842365525503581863[186] = 0.0;
   out_2842365525503581863[187] = 0.0;
   out_2842365525503581863[188] = 0.0;
   out_2842365525503581863[189] = 0.0;
   out_2842365525503581863[190] = 1.0;
   out_2842365525503581863[191] = 0.0;
   out_2842365525503581863[192] = 0.0;
   out_2842365525503581863[193] = 0.0;
   out_2842365525503581863[194] = 0.0;
   out_2842365525503581863[195] = 0.0;
   out_2842365525503581863[196] = 0.0;
   out_2842365525503581863[197] = 0.0;
   out_2842365525503581863[198] = 0.0;
   out_2842365525503581863[199] = 0.0;
   out_2842365525503581863[200] = 0.0;
   out_2842365525503581863[201] = 0.0;
   out_2842365525503581863[202] = 0.0;
   out_2842365525503581863[203] = 0.0;
   out_2842365525503581863[204] = 0.0;
   out_2842365525503581863[205] = 0.0;
   out_2842365525503581863[206] = 0.0;
   out_2842365525503581863[207] = 0.0;
   out_2842365525503581863[208] = 0.0;
   out_2842365525503581863[209] = 1.0;
   out_2842365525503581863[210] = 0.0;
   out_2842365525503581863[211] = 0.0;
   out_2842365525503581863[212] = 0.0;
   out_2842365525503581863[213] = 0.0;
   out_2842365525503581863[214] = 0.0;
   out_2842365525503581863[215] = 0.0;
   out_2842365525503581863[216] = 0.0;
   out_2842365525503581863[217] = 0.0;
   out_2842365525503581863[218] = 0.0;
   out_2842365525503581863[219] = 0.0;
   out_2842365525503581863[220] = 0.0;
   out_2842365525503581863[221] = 0.0;
   out_2842365525503581863[222] = 0.0;
   out_2842365525503581863[223] = 0.0;
   out_2842365525503581863[224] = 0.0;
   out_2842365525503581863[225] = 0.0;
   out_2842365525503581863[226] = 0.0;
   out_2842365525503581863[227] = 0.0;
   out_2842365525503581863[228] = 1.0;
   out_2842365525503581863[229] = 0.0;
   out_2842365525503581863[230] = 0.0;
   out_2842365525503581863[231] = 0.0;
   out_2842365525503581863[232] = 0.0;
   out_2842365525503581863[233] = 0.0;
   out_2842365525503581863[234] = 0.0;
   out_2842365525503581863[235] = 0.0;
   out_2842365525503581863[236] = 0.0;
   out_2842365525503581863[237] = 0.0;
   out_2842365525503581863[238] = 0.0;
   out_2842365525503581863[239] = 0.0;
   out_2842365525503581863[240] = 0.0;
   out_2842365525503581863[241] = 0.0;
   out_2842365525503581863[242] = 0.0;
   out_2842365525503581863[243] = 0.0;
   out_2842365525503581863[244] = 0.0;
   out_2842365525503581863[245] = 0.0;
   out_2842365525503581863[246] = 0.0;
   out_2842365525503581863[247] = 1.0;
   out_2842365525503581863[248] = 0.0;
   out_2842365525503581863[249] = 0.0;
   out_2842365525503581863[250] = 0.0;
   out_2842365525503581863[251] = 0.0;
   out_2842365525503581863[252] = 0.0;
   out_2842365525503581863[253] = 0.0;
   out_2842365525503581863[254] = 0.0;
   out_2842365525503581863[255] = 0.0;
   out_2842365525503581863[256] = 0.0;
   out_2842365525503581863[257] = 0.0;
   out_2842365525503581863[258] = 0.0;
   out_2842365525503581863[259] = 0.0;
   out_2842365525503581863[260] = 0.0;
   out_2842365525503581863[261] = 0.0;
   out_2842365525503581863[262] = 0.0;
   out_2842365525503581863[263] = 0.0;
   out_2842365525503581863[264] = 0.0;
   out_2842365525503581863[265] = 0.0;
   out_2842365525503581863[266] = 1.0;
   out_2842365525503581863[267] = 0.0;
   out_2842365525503581863[268] = 0.0;
   out_2842365525503581863[269] = 0.0;
   out_2842365525503581863[270] = 0.0;
   out_2842365525503581863[271] = 0.0;
   out_2842365525503581863[272] = 0.0;
   out_2842365525503581863[273] = 0.0;
   out_2842365525503581863[274] = 0.0;
   out_2842365525503581863[275] = 0.0;
   out_2842365525503581863[276] = 0.0;
   out_2842365525503581863[277] = 0.0;
   out_2842365525503581863[278] = 0.0;
   out_2842365525503581863[279] = 0.0;
   out_2842365525503581863[280] = 0.0;
   out_2842365525503581863[281] = 0.0;
   out_2842365525503581863[282] = 0.0;
   out_2842365525503581863[283] = 0.0;
   out_2842365525503581863[284] = 0.0;
   out_2842365525503581863[285] = 1.0;
   out_2842365525503581863[286] = 0.0;
   out_2842365525503581863[287] = 0.0;
   out_2842365525503581863[288] = 0.0;
   out_2842365525503581863[289] = 0.0;
   out_2842365525503581863[290] = 0.0;
   out_2842365525503581863[291] = 0.0;
   out_2842365525503581863[292] = 0.0;
   out_2842365525503581863[293] = 0.0;
   out_2842365525503581863[294] = 0.0;
   out_2842365525503581863[295] = 0.0;
   out_2842365525503581863[296] = 0.0;
   out_2842365525503581863[297] = 0.0;
   out_2842365525503581863[298] = 0.0;
   out_2842365525503581863[299] = 0.0;
   out_2842365525503581863[300] = 0.0;
   out_2842365525503581863[301] = 0.0;
   out_2842365525503581863[302] = 0.0;
   out_2842365525503581863[303] = 0.0;
   out_2842365525503581863[304] = 1.0;
   out_2842365525503581863[305] = 0.0;
   out_2842365525503581863[306] = 0.0;
   out_2842365525503581863[307] = 0.0;
   out_2842365525503581863[308] = 0.0;
   out_2842365525503581863[309] = 0.0;
   out_2842365525503581863[310] = 0.0;
   out_2842365525503581863[311] = 0.0;
   out_2842365525503581863[312] = 0.0;
   out_2842365525503581863[313] = 0.0;
   out_2842365525503581863[314] = 0.0;
   out_2842365525503581863[315] = 0.0;
   out_2842365525503581863[316] = 0.0;
   out_2842365525503581863[317] = 0.0;
   out_2842365525503581863[318] = 0.0;
   out_2842365525503581863[319] = 0.0;
   out_2842365525503581863[320] = 0.0;
   out_2842365525503581863[321] = 0.0;
   out_2842365525503581863[322] = 0.0;
   out_2842365525503581863[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4467642216364550642) {
   out_4467642216364550642[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4467642216364550642[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4467642216364550642[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4467642216364550642[3] = dt*state[12] + state[3];
   out_4467642216364550642[4] = dt*state[13] + state[4];
   out_4467642216364550642[5] = dt*state[14] + state[5];
   out_4467642216364550642[6] = state[6];
   out_4467642216364550642[7] = state[7];
   out_4467642216364550642[8] = state[8];
   out_4467642216364550642[9] = state[9];
   out_4467642216364550642[10] = state[10];
   out_4467642216364550642[11] = state[11];
   out_4467642216364550642[12] = state[12];
   out_4467642216364550642[13] = state[13];
   out_4467642216364550642[14] = state[14];
   out_4467642216364550642[15] = state[15];
   out_4467642216364550642[16] = state[16];
   out_4467642216364550642[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6705233003971863459) {
   out_6705233003971863459[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6705233003971863459[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6705233003971863459[2] = 0;
   out_6705233003971863459[3] = 0;
   out_6705233003971863459[4] = 0;
   out_6705233003971863459[5] = 0;
   out_6705233003971863459[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6705233003971863459[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6705233003971863459[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6705233003971863459[9] = 0;
   out_6705233003971863459[10] = 0;
   out_6705233003971863459[11] = 0;
   out_6705233003971863459[12] = 0;
   out_6705233003971863459[13] = 0;
   out_6705233003971863459[14] = 0;
   out_6705233003971863459[15] = 0;
   out_6705233003971863459[16] = 0;
   out_6705233003971863459[17] = 0;
   out_6705233003971863459[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6705233003971863459[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6705233003971863459[20] = 0;
   out_6705233003971863459[21] = 0;
   out_6705233003971863459[22] = 0;
   out_6705233003971863459[23] = 0;
   out_6705233003971863459[24] = 0;
   out_6705233003971863459[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6705233003971863459[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6705233003971863459[27] = 0;
   out_6705233003971863459[28] = 0;
   out_6705233003971863459[29] = 0;
   out_6705233003971863459[30] = 0;
   out_6705233003971863459[31] = 0;
   out_6705233003971863459[32] = 0;
   out_6705233003971863459[33] = 0;
   out_6705233003971863459[34] = 0;
   out_6705233003971863459[35] = 0;
   out_6705233003971863459[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6705233003971863459[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6705233003971863459[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6705233003971863459[39] = 0;
   out_6705233003971863459[40] = 0;
   out_6705233003971863459[41] = 0;
   out_6705233003971863459[42] = 0;
   out_6705233003971863459[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6705233003971863459[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6705233003971863459[45] = 0;
   out_6705233003971863459[46] = 0;
   out_6705233003971863459[47] = 0;
   out_6705233003971863459[48] = 0;
   out_6705233003971863459[49] = 0;
   out_6705233003971863459[50] = 0;
   out_6705233003971863459[51] = 0;
   out_6705233003971863459[52] = 0;
   out_6705233003971863459[53] = 0;
   out_6705233003971863459[54] = 0;
   out_6705233003971863459[55] = 0;
   out_6705233003971863459[56] = 0;
   out_6705233003971863459[57] = 1;
   out_6705233003971863459[58] = 0;
   out_6705233003971863459[59] = 0;
   out_6705233003971863459[60] = 0;
   out_6705233003971863459[61] = 0;
   out_6705233003971863459[62] = 0;
   out_6705233003971863459[63] = 0;
   out_6705233003971863459[64] = 0;
   out_6705233003971863459[65] = 0;
   out_6705233003971863459[66] = dt;
   out_6705233003971863459[67] = 0;
   out_6705233003971863459[68] = 0;
   out_6705233003971863459[69] = 0;
   out_6705233003971863459[70] = 0;
   out_6705233003971863459[71] = 0;
   out_6705233003971863459[72] = 0;
   out_6705233003971863459[73] = 0;
   out_6705233003971863459[74] = 0;
   out_6705233003971863459[75] = 0;
   out_6705233003971863459[76] = 1;
   out_6705233003971863459[77] = 0;
   out_6705233003971863459[78] = 0;
   out_6705233003971863459[79] = 0;
   out_6705233003971863459[80] = 0;
   out_6705233003971863459[81] = 0;
   out_6705233003971863459[82] = 0;
   out_6705233003971863459[83] = 0;
   out_6705233003971863459[84] = 0;
   out_6705233003971863459[85] = dt;
   out_6705233003971863459[86] = 0;
   out_6705233003971863459[87] = 0;
   out_6705233003971863459[88] = 0;
   out_6705233003971863459[89] = 0;
   out_6705233003971863459[90] = 0;
   out_6705233003971863459[91] = 0;
   out_6705233003971863459[92] = 0;
   out_6705233003971863459[93] = 0;
   out_6705233003971863459[94] = 0;
   out_6705233003971863459[95] = 1;
   out_6705233003971863459[96] = 0;
   out_6705233003971863459[97] = 0;
   out_6705233003971863459[98] = 0;
   out_6705233003971863459[99] = 0;
   out_6705233003971863459[100] = 0;
   out_6705233003971863459[101] = 0;
   out_6705233003971863459[102] = 0;
   out_6705233003971863459[103] = 0;
   out_6705233003971863459[104] = dt;
   out_6705233003971863459[105] = 0;
   out_6705233003971863459[106] = 0;
   out_6705233003971863459[107] = 0;
   out_6705233003971863459[108] = 0;
   out_6705233003971863459[109] = 0;
   out_6705233003971863459[110] = 0;
   out_6705233003971863459[111] = 0;
   out_6705233003971863459[112] = 0;
   out_6705233003971863459[113] = 0;
   out_6705233003971863459[114] = 1;
   out_6705233003971863459[115] = 0;
   out_6705233003971863459[116] = 0;
   out_6705233003971863459[117] = 0;
   out_6705233003971863459[118] = 0;
   out_6705233003971863459[119] = 0;
   out_6705233003971863459[120] = 0;
   out_6705233003971863459[121] = 0;
   out_6705233003971863459[122] = 0;
   out_6705233003971863459[123] = 0;
   out_6705233003971863459[124] = 0;
   out_6705233003971863459[125] = 0;
   out_6705233003971863459[126] = 0;
   out_6705233003971863459[127] = 0;
   out_6705233003971863459[128] = 0;
   out_6705233003971863459[129] = 0;
   out_6705233003971863459[130] = 0;
   out_6705233003971863459[131] = 0;
   out_6705233003971863459[132] = 0;
   out_6705233003971863459[133] = 1;
   out_6705233003971863459[134] = 0;
   out_6705233003971863459[135] = 0;
   out_6705233003971863459[136] = 0;
   out_6705233003971863459[137] = 0;
   out_6705233003971863459[138] = 0;
   out_6705233003971863459[139] = 0;
   out_6705233003971863459[140] = 0;
   out_6705233003971863459[141] = 0;
   out_6705233003971863459[142] = 0;
   out_6705233003971863459[143] = 0;
   out_6705233003971863459[144] = 0;
   out_6705233003971863459[145] = 0;
   out_6705233003971863459[146] = 0;
   out_6705233003971863459[147] = 0;
   out_6705233003971863459[148] = 0;
   out_6705233003971863459[149] = 0;
   out_6705233003971863459[150] = 0;
   out_6705233003971863459[151] = 0;
   out_6705233003971863459[152] = 1;
   out_6705233003971863459[153] = 0;
   out_6705233003971863459[154] = 0;
   out_6705233003971863459[155] = 0;
   out_6705233003971863459[156] = 0;
   out_6705233003971863459[157] = 0;
   out_6705233003971863459[158] = 0;
   out_6705233003971863459[159] = 0;
   out_6705233003971863459[160] = 0;
   out_6705233003971863459[161] = 0;
   out_6705233003971863459[162] = 0;
   out_6705233003971863459[163] = 0;
   out_6705233003971863459[164] = 0;
   out_6705233003971863459[165] = 0;
   out_6705233003971863459[166] = 0;
   out_6705233003971863459[167] = 0;
   out_6705233003971863459[168] = 0;
   out_6705233003971863459[169] = 0;
   out_6705233003971863459[170] = 0;
   out_6705233003971863459[171] = 1;
   out_6705233003971863459[172] = 0;
   out_6705233003971863459[173] = 0;
   out_6705233003971863459[174] = 0;
   out_6705233003971863459[175] = 0;
   out_6705233003971863459[176] = 0;
   out_6705233003971863459[177] = 0;
   out_6705233003971863459[178] = 0;
   out_6705233003971863459[179] = 0;
   out_6705233003971863459[180] = 0;
   out_6705233003971863459[181] = 0;
   out_6705233003971863459[182] = 0;
   out_6705233003971863459[183] = 0;
   out_6705233003971863459[184] = 0;
   out_6705233003971863459[185] = 0;
   out_6705233003971863459[186] = 0;
   out_6705233003971863459[187] = 0;
   out_6705233003971863459[188] = 0;
   out_6705233003971863459[189] = 0;
   out_6705233003971863459[190] = 1;
   out_6705233003971863459[191] = 0;
   out_6705233003971863459[192] = 0;
   out_6705233003971863459[193] = 0;
   out_6705233003971863459[194] = 0;
   out_6705233003971863459[195] = 0;
   out_6705233003971863459[196] = 0;
   out_6705233003971863459[197] = 0;
   out_6705233003971863459[198] = 0;
   out_6705233003971863459[199] = 0;
   out_6705233003971863459[200] = 0;
   out_6705233003971863459[201] = 0;
   out_6705233003971863459[202] = 0;
   out_6705233003971863459[203] = 0;
   out_6705233003971863459[204] = 0;
   out_6705233003971863459[205] = 0;
   out_6705233003971863459[206] = 0;
   out_6705233003971863459[207] = 0;
   out_6705233003971863459[208] = 0;
   out_6705233003971863459[209] = 1;
   out_6705233003971863459[210] = 0;
   out_6705233003971863459[211] = 0;
   out_6705233003971863459[212] = 0;
   out_6705233003971863459[213] = 0;
   out_6705233003971863459[214] = 0;
   out_6705233003971863459[215] = 0;
   out_6705233003971863459[216] = 0;
   out_6705233003971863459[217] = 0;
   out_6705233003971863459[218] = 0;
   out_6705233003971863459[219] = 0;
   out_6705233003971863459[220] = 0;
   out_6705233003971863459[221] = 0;
   out_6705233003971863459[222] = 0;
   out_6705233003971863459[223] = 0;
   out_6705233003971863459[224] = 0;
   out_6705233003971863459[225] = 0;
   out_6705233003971863459[226] = 0;
   out_6705233003971863459[227] = 0;
   out_6705233003971863459[228] = 1;
   out_6705233003971863459[229] = 0;
   out_6705233003971863459[230] = 0;
   out_6705233003971863459[231] = 0;
   out_6705233003971863459[232] = 0;
   out_6705233003971863459[233] = 0;
   out_6705233003971863459[234] = 0;
   out_6705233003971863459[235] = 0;
   out_6705233003971863459[236] = 0;
   out_6705233003971863459[237] = 0;
   out_6705233003971863459[238] = 0;
   out_6705233003971863459[239] = 0;
   out_6705233003971863459[240] = 0;
   out_6705233003971863459[241] = 0;
   out_6705233003971863459[242] = 0;
   out_6705233003971863459[243] = 0;
   out_6705233003971863459[244] = 0;
   out_6705233003971863459[245] = 0;
   out_6705233003971863459[246] = 0;
   out_6705233003971863459[247] = 1;
   out_6705233003971863459[248] = 0;
   out_6705233003971863459[249] = 0;
   out_6705233003971863459[250] = 0;
   out_6705233003971863459[251] = 0;
   out_6705233003971863459[252] = 0;
   out_6705233003971863459[253] = 0;
   out_6705233003971863459[254] = 0;
   out_6705233003971863459[255] = 0;
   out_6705233003971863459[256] = 0;
   out_6705233003971863459[257] = 0;
   out_6705233003971863459[258] = 0;
   out_6705233003971863459[259] = 0;
   out_6705233003971863459[260] = 0;
   out_6705233003971863459[261] = 0;
   out_6705233003971863459[262] = 0;
   out_6705233003971863459[263] = 0;
   out_6705233003971863459[264] = 0;
   out_6705233003971863459[265] = 0;
   out_6705233003971863459[266] = 1;
   out_6705233003971863459[267] = 0;
   out_6705233003971863459[268] = 0;
   out_6705233003971863459[269] = 0;
   out_6705233003971863459[270] = 0;
   out_6705233003971863459[271] = 0;
   out_6705233003971863459[272] = 0;
   out_6705233003971863459[273] = 0;
   out_6705233003971863459[274] = 0;
   out_6705233003971863459[275] = 0;
   out_6705233003971863459[276] = 0;
   out_6705233003971863459[277] = 0;
   out_6705233003971863459[278] = 0;
   out_6705233003971863459[279] = 0;
   out_6705233003971863459[280] = 0;
   out_6705233003971863459[281] = 0;
   out_6705233003971863459[282] = 0;
   out_6705233003971863459[283] = 0;
   out_6705233003971863459[284] = 0;
   out_6705233003971863459[285] = 1;
   out_6705233003971863459[286] = 0;
   out_6705233003971863459[287] = 0;
   out_6705233003971863459[288] = 0;
   out_6705233003971863459[289] = 0;
   out_6705233003971863459[290] = 0;
   out_6705233003971863459[291] = 0;
   out_6705233003971863459[292] = 0;
   out_6705233003971863459[293] = 0;
   out_6705233003971863459[294] = 0;
   out_6705233003971863459[295] = 0;
   out_6705233003971863459[296] = 0;
   out_6705233003971863459[297] = 0;
   out_6705233003971863459[298] = 0;
   out_6705233003971863459[299] = 0;
   out_6705233003971863459[300] = 0;
   out_6705233003971863459[301] = 0;
   out_6705233003971863459[302] = 0;
   out_6705233003971863459[303] = 0;
   out_6705233003971863459[304] = 1;
   out_6705233003971863459[305] = 0;
   out_6705233003971863459[306] = 0;
   out_6705233003971863459[307] = 0;
   out_6705233003971863459[308] = 0;
   out_6705233003971863459[309] = 0;
   out_6705233003971863459[310] = 0;
   out_6705233003971863459[311] = 0;
   out_6705233003971863459[312] = 0;
   out_6705233003971863459[313] = 0;
   out_6705233003971863459[314] = 0;
   out_6705233003971863459[315] = 0;
   out_6705233003971863459[316] = 0;
   out_6705233003971863459[317] = 0;
   out_6705233003971863459[318] = 0;
   out_6705233003971863459[319] = 0;
   out_6705233003971863459[320] = 0;
   out_6705233003971863459[321] = 0;
   out_6705233003971863459[322] = 0;
   out_6705233003971863459[323] = 1;
}
void h_4(double *state, double *unused, double *out_2420505654720678801) {
   out_2420505654720678801[0] = state[6] + state[9];
   out_2420505654720678801[1] = state[7] + state[10];
   out_2420505654720678801[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7994883910542662598) {
   out_7994883910542662598[0] = 0;
   out_7994883910542662598[1] = 0;
   out_7994883910542662598[2] = 0;
   out_7994883910542662598[3] = 0;
   out_7994883910542662598[4] = 0;
   out_7994883910542662598[5] = 0;
   out_7994883910542662598[6] = 1;
   out_7994883910542662598[7] = 0;
   out_7994883910542662598[8] = 0;
   out_7994883910542662598[9] = 1;
   out_7994883910542662598[10] = 0;
   out_7994883910542662598[11] = 0;
   out_7994883910542662598[12] = 0;
   out_7994883910542662598[13] = 0;
   out_7994883910542662598[14] = 0;
   out_7994883910542662598[15] = 0;
   out_7994883910542662598[16] = 0;
   out_7994883910542662598[17] = 0;
   out_7994883910542662598[18] = 0;
   out_7994883910542662598[19] = 0;
   out_7994883910542662598[20] = 0;
   out_7994883910542662598[21] = 0;
   out_7994883910542662598[22] = 0;
   out_7994883910542662598[23] = 0;
   out_7994883910542662598[24] = 0;
   out_7994883910542662598[25] = 1;
   out_7994883910542662598[26] = 0;
   out_7994883910542662598[27] = 0;
   out_7994883910542662598[28] = 1;
   out_7994883910542662598[29] = 0;
   out_7994883910542662598[30] = 0;
   out_7994883910542662598[31] = 0;
   out_7994883910542662598[32] = 0;
   out_7994883910542662598[33] = 0;
   out_7994883910542662598[34] = 0;
   out_7994883910542662598[35] = 0;
   out_7994883910542662598[36] = 0;
   out_7994883910542662598[37] = 0;
   out_7994883910542662598[38] = 0;
   out_7994883910542662598[39] = 0;
   out_7994883910542662598[40] = 0;
   out_7994883910542662598[41] = 0;
   out_7994883910542662598[42] = 0;
   out_7994883910542662598[43] = 0;
   out_7994883910542662598[44] = 1;
   out_7994883910542662598[45] = 0;
   out_7994883910542662598[46] = 0;
   out_7994883910542662598[47] = 1;
   out_7994883910542662598[48] = 0;
   out_7994883910542662598[49] = 0;
   out_7994883910542662598[50] = 0;
   out_7994883910542662598[51] = 0;
   out_7994883910542662598[52] = 0;
   out_7994883910542662598[53] = 0;
}
void h_10(double *state, double *unused, double *out_2313242717828257647) {
   out_2313242717828257647[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2313242717828257647[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2313242717828257647[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5472455547052034825) {
   out_5472455547052034825[0] = 0;
   out_5472455547052034825[1] = 9.8100000000000005*cos(state[1]);
   out_5472455547052034825[2] = 0;
   out_5472455547052034825[3] = 0;
   out_5472455547052034825[4] = -state[8];
   out_5472455547052034825[5] = state[7];
   out_5472455547052034825[6] = 0;
   out_5472455547052034825[7] = state[5];
   out_5472455547052034825[8] = -state[4];
   out_5472455547052034825[9] = 0;
   out_5472455547052034825[10] = 0;
   out_5472455547052034825[11] = 0;
   out_5472455547052034825[12] = 1;
   out_5472455547052034825[13] = 0;
   out_5472455547052034825[14] = 0;
   out_5472455547052034825[15] = 1;
   out_5472455547052034825[16] = 0;
   out_5472455547052034825[17] = 0;
   out_5472455547052034825[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5472455547052034825[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5472455547052034825[20] = 0;
   out_5472455547052034825[21] = state[8];
   out_5472455547052034825[22] = 0;
   out_5472455547052034825[23] = -state[6];
   out_5472455547052034825[24] = -state[5];
   out_5472455547052034825[25] = 0;
   out_5472455547052034825[26] = state[3];
   out_5472455547052034825[27] = 0;
   out_5472455547052034825[28] = 0;
   out_5472455547052034825[29] = 0;
   out_5472455547052034825[30] = 0;
   out_5472455547052034825[31] = 1;
   out_5472455547052034825[32] = 0;
   out_5472455547052034825[33] = 0;
   out_5472455547052034825[34] = 1;
   out_5472455547052034825[35] = 0;
   out_5472455547052034825[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5472455547052034825[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5472455547052034825[38] = 0;
   out_5472455547052034825[39] = -state[7];
   out_5472455547052034825[40] = state[6];
   out_5472455547052034825[41] = 0;
   out_5472455547052034825[42] = state[4];
   out_5472455547052034825[43] = -state[3];
   out_5472455547052034825[44] = 0;
   out_5472455547052034825[45] = 0;
   out_5472455547052034825[46] = 0;
   out_5472455547052034825[47] = 0;
   out_5472455547052034825[48] = 0;
   out_5472455547052034825[49] = 0;
   out_5472455547052034825[50] = 1;
   out_5472455547052034825[51] = 0;
   out_5472455547052034825[52] = 0;
   out_5472455547052034825[53] = 1;
}
void h_13(double *state, double *unused, double *out_5520356542441325623) {
   out_5520356542441325623[0] = state[3];
   out_5520356542441325623[1] = state[4];
   out_5520356542441325623[2] = state[5];
}
void H_13(double *state, double *unused, double *out_7239586337834556217) {
   out_7239586337834556217[0] = 0;
   out_7239586337834556217[1] = 0;
   out_7239586337834556217[2] = 0;
   out_7239586337834556217[3] = 1;
   out_7239586337834556217[4] = 0;
   out_7239586337834556217[5] = 0;
   out_7239586337834556217[6] = 0;
   out_7239586337834556217[7] = 0;
   out_7239586337834556217[8] = 0;
   out_7239586337834556217[9] = 0;
   out_7239586337834556217[10] = 0;
   out_7239586337834556217[11] = 0;
   out_7239586337834556217[12] = 0;
   out_7239586337834556217[13] = 0;
   out_7239586337834556217[14] = 0;
   out_7239586337834556217[15] = 0;
   out_7239586337834556217[16] = 0;
   out_7239586337834556217[17] = 0;
   out_7239586337834556217[18] = 0;
   out_7239586337834556217[19] = 0;
   out_7239586337834556217[20] = 0;
   out_7239586337834556217[21] = 0;
   out_7239586337834556217[22] = 1;
   out_7239586337834556217[23] = 0;
   out_7239586337834556217[24] = 0;
   out_7239586337834556217[25] = 0;
   out_7239586337834556217[26] = 0;
   out_7239586337834556217[27] = 0;
   out_7239586337834556217[28] = 0;
   out_7239586337834556217[29] = 0;
   out_7239586337834556217[30] = 0;
   out_7239586337834556217[31] = 0;
   out_7239586337834556217[32] = 0;
   out_7239586337834556217[33] = 0;
   out_7239586337834556217[34] = 0;
   out_7239586337834556217[35] = 0;
   out_7239586337834556217[36] = 0;
   out_7239586337834556217[37] = 0;
   out_7239586337834556217[38] = 0;
   out_7239586337834556217[39] = 0;
   out_7239586337834556217[40] = 0;
   out_7239586337834556217[41] = 1;
   out_7239586337834556217[42] = 0;
   out_7239586337834556217[43] = 0;
   out_7239586337834556217[44] = 0;
   out_7239586337834556217[45] = 0;
   out_7239586337834556217[46] = 0;
   out_7239586337834556217[47] = 0;
   out_7239586337834556217[48] = 0;
   out_7239586337834556217[49] = 0;
   out_7239586337834556217[50] = 0;
   out_7239586337834556217[51] = 0;
   out_7239586337834556217[52] = 0;
   out_7239586337834556217[53] = 0;
}
void h_14(double *state, double *unused, double *out_8136982398563814036) {
   out_8136982398563814036[0] = state[6];
   out_8136982398563814036[1] = state[7];
   out_8136982398563814036[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6488619306827404489) {
   out_6488619306827404489[0] = 0;
   out_6488619306827404489[1] = 0;
   out_6488619306827404489[2] = 0;
   out_6488619306827404489[3] = 0;
   out_6488619306827404489[4] = 0;
   out_6488619306827404489[5] = 0;
   out_6488619306827404489[6] = 1;
   out_6488619306827404489[7] = 0;
   out_6488619306827404489[8] = 0;
   out_6488619306827404489[9] = 0;
   out_6488619306827404489[10] = 0;
   out_6488619306827404489[11] = 0;
   out_6488619306827404489[12] = 0;
   out_6488619306827404489[13] = 0;
   out_6488619306827404489[14] = 0;
   out_6488619306827404489[15] = 0;
   out_6488619306827404489[16] = 0;
   out_6488619306827404489[17] = 0;
   out_6488619306827404489[18] = 0;
   out_6488619306827404489[19] = 0;
   out_6488619306827404489[20] = 0;
   out_6488619306827404489[21] = 0;
   out_6488619306827404489[22] = 0;
   out_6488619306827404489[23] = 0;
   out_6488619306827404489[24] = 0;
   out_6488619306827404489[25] = 1;
   out_6488619306827404489[26] = 0;
   out_6488619306827404489[27] = 0;
   out_6488619306827404489[28] = 0;
   out_6488619306827404489[29] = 0;
   out_6488619306827404489[30] = 0;
   out_6488619306827404489[31] = 0;
   out_6488619306827404489[32] = 0;
   out_6488619306827404489[33] = 0;
   out_6488619306827404489[34] = 0;
   out_6488619306827404489[35] = 0;
   out_6488619306827404489[36] = 0;
   out_6488619306827404489[37] = 0;
   out_6488619306827404489[38] = 0;
   out_6488619306827404489[39] = 0;
   out_6488619306827404489[40] = 0;
   out_6488619306827404489[41] = 0;
   out_6488619306827404489[42] = 0;
   out_6488619306827404489[43] = 0;
   out_6488619306827404489[44] = 1;
   out_6488619306827404489[45] = 0;
   out_6488619306827404489[46] = 0;
   out_6488619306827404489[47] = 0;
   out_6488619306827404489[48] = 0;
   out_6488619306827404489[49] = 0;
   out_6488619306827404489[50] = 0;
   out_6488619306827404489[51] = 0;
   out_6488619306827404489[52] = 0;
   out_6488619306827404489[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_1314885097679334068) {
  err_fun(nom_x, delta_x, out_1314885097679334068);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2457185809051772100) {
  inv_err_fun(nom_x, true_x, out_2457185809051772100);
}
void pose_H_mod_fun(double *state, double *out_2842365525503581863) {
  H_mod_fun(state, out_2842365525503581863);
}
void pose_f_fun(double *state, double dt, double *out_4467642216364550642) {
  f_fun(state,  dt, out_4467642216364550642);
}
void pose_F_fun(double *state, double dt, double *out_6705233003971863459) {
  F_fun(state,  dt, out_6705233003971863459);
}
void pose_h_4(double *state, double *unused, double *out_2420505654720678801) {
  h_4(state, unused, out_2420505654720678801);
}
void pose_H_4(double *state, double *unused, double *out_7994883910542662598) {
  H_4(state, unused, out_7994883910542662598);
}
void pose_h_10(double *state, double *unused, double *out_2313242717828257647) {
  h_10(state, unused, out_2313242717828257647);
}
void pose_H_10(double *state, double *unused, double *out_5472455547052034825) {
  H_10(state, unused, out_5472455547052034825);
}
void pose_h_13(double *state, double *unused, double *out_5520356542441325623) {
  h_13(state, unused, out_5520356542441325623);
}
void pose_H_13(double *state, double *unused, double *out_7239586337834556217) {
  H_13(state, unused, out_7239586337834556217);
}
void pose_h_14(double *state, double *unused, double *out_8136982398563814036) {
  h_14(state, unused, out_8136982398563814036);
}
void pose_H_14(double *state, double *unused, double *out_6488619306827404489) {
  H_14(state, unused, out_6488619306827404489);
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
