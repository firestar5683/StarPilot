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
void err_fun(double *nom_x, double *delta_x, double *out_3784924644306313628) {
   out_3784924644306313628[0] = delta_x[0] + nom_x[0];
   out_3784924644306313628[1] = delta_x[1] + nom_x[1];
   out_3784924644306313628[2] = delta_x[2] + nom_x[2];
   out_3784924644306313628[3] = delta_x[3] + nom_x[3];
   out_3784924644306313628[4] = delta_x[4] + nom_x[4];
   out_3784924644306313628[5] = delta_x[5] + nom_x[5];
   out_3784924644306313628[6] = delta_x[6] + nom_x[6];
   out_3784924644306313628[7] = delta_x[7] + nom_x[7];
   out_3784924644306313628[8] = delta_x[8] + nom_x[8];
   out_3784924644306313628[9] = delta_x[9] + nom_x[9];
   out_3784924644306313628[10] = delta_x[10] + nom_x[10];
   out_3784924644306313628[11] = delta_x[11] + nom_x[11];
   out_3784924644306313628[12] = delta_x[12] + nom_x[12];
   out_3784924644306313628[13] = delta_x[13] + nom_x[13];
   out_3784924644306313628[14] = delta_x[14] + nom_x[14];
   out_3784924644306313628[15] = delta_x[15] + nom_x[15];
   out_3784924644306313628[16] = delta_x[16] + nom_x[16];
   out_3784924644306313628[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_540309216742292633) {
   out_540309216742292633[0] = -nom_x[0] + true_x[0];
   out_540309216742292633[1] = -nom_x[1] + true_x[1];
   out_540309216742292633[2] = -nom_x[2] + true_x[2];
   out_540309216742292633[3] = -nom_x[3] + true_x[3];
   out_540309216742292633[4] = -nom_x[4] + true_x[4];
   out_540309216742292633[5] = -nom_x[5] + true_x[5];
   out_540309216742292633[6] = -nom_x[6] + true_x[6];
   out_540309216742292633[7] = -nom_x[7] + true_x[7];
   out_540309216742292633[8] = -nom_x[8] + true_x[8];
   out_540309216742292633[9] = -nom_x[9] + true_x[9];
   out_540309216742292633[10] = -nom_x[10] + true_x[10];
   out_540309216742292633[11] = -nom_x[11] + true_x[11];
   out_540309216742292633[12] = -nom_x[12] + true_x[12];
   out_540309216742292633[13] = -nom_x[13] + true_x[13];
   out_540309216742292633[14] = -nom_x[14] + true_x[14];
   out_540309216742292633[15] = -nom_x[15] + true_x[15];
   out_540309216742292633[16] = -nom_x[16] + true_x[16];
   out_540309216742292633[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6508658752892015980) {
   out_6508658752892015980[0] = 1.0;
   out_6508658752892015980[1] = 0.0;
   out_6508658752892015980[2] = 0.0;
   out_6508658752892015980[3] = 0.0;
   out_6508658752892015980[4] = 0.0;
   out_6508658752892015980[5] = 0.0;
   out_6508658752892015980[6] = 0.0;
   out_6508658752892015980[7] = 0.0;
   out_6508658752892015980[8] = 0.0;
   out_6508658752892015980[9] = 0.0;
   out_6508658752892015980[10] = 0.0;
   out_6508658752892015980[11] = 0.0;
   out_6508658752892015980[12] = 0.0;
   out_6508658752892015980[13] = 0.0;
   out_6508658752892015980[14] = 0.0;
   out_6508658752892015980[15] = 0.0;
   out_6508658752892015980[16] = 0.0;
   out_6508658752892015980[17] = 0.0;
   out_6508658752892015980[18] = 0.0;
   out_6508658752892015980[19] = 1.0;
   out_6508658752892015980[20] = 0.0;
   out_6508658752892015980[21] = 0.0;
   out_6508658752892015980[22] = 0.0;
   out_6508658752892015980[23] = 0.0;
   out_6508658752892015980[24] = 0.0;
   out_6508658752892015980[25] = 0.0;
   out_6508658752892015980[26] = 0.0;
   out_6508658752892015980[27] = 0.0;
   out_6508658752892015980[28] = 0.0;
   out_6508658752892015980[29] = 0.0;
   out_6508658752892015980[30] = 0.0;
   out_6508658752892015980[31] = 0.0;
   out_6508658752892015980[32] = 0.0;
   out_6508658752892015980[33] = 0.0;
   out_6508658752892015980[34] = 0.0;
   out_6508658752892015980[35] = 0.0;
   out_6508658752892015980[36] = 0.0;
   out_6508658752892015980[37] = 0.0;
   out_6508658752892015980[38] = 1.0;
   out_6508658752892015980[39] = 0.0;
   out_6508658752892015980[40] = 0.0;
   out_6508658752892015980[41] = 0.0;
   out_6508658752892015980[42] = 0.0;
   out_6508658752892015980[43] = 0.0;
   out_6508658752892015980[44] = 0.0;
   out_6508658752892015980[45] = 0.0;
   out_6508658752892015980[46] = 0.0;
   out_6508658752892015980[47] = 0.0;
   out_6508658752892015980[48] = 0.0;
   out_6508658752892015980[49] = 0.0;
   out_6508658752892015980[50] = 0.0;
   out_6508658752892015980[51] = 0.0;
   out_6508658752892015980[52] = 0.0;
   out_6508658752892015980[53] = 0.0;
   out_6508658752892015980[54] = 0.0;
   out_6508658752892015980[55] = 0.0;
   out_6508658752892015980[56] = 0.0;
   out_6508658752892015980[57] = 1.0;
   out_6508658752892015980[58] = 0.0;
   out_6508658752892015980[59] = 0.0;
   out_6508658752892015980[60] = 0.0;
   out_6508658752892015980[61] = 0.0;
   out_6508658752892015980[62] = 0.0;
   out_6508658752892015980[63] = 0.0;
   out_6508658752892015980[64] = 0.0;
   out_6508658752892015980[65] = 0.0;
   out_6508658752892015980[66] = 0.0;
   out_6508658752892015980[67] = 0.0;
   out_6508658752892015980[68] = 0.0;
   out_6508658752892015980[69] = 0.0;
   out_6508658752892015980[70] = 0.0;
   out_6508658752892015980[71] = 0.0;
   out_6508658752892015980[72] = 0.0;
   out_6508658752892015980[73] = 0.0;
   out_6508658752892015980[74] = 0.0;
   out_6508658752892015980[75] = 0.0;
   out_6508658752892015980[76] = 1.0;
   out_6508658752892015980[77] = 0.0;
   out_6508658752892015980[78] = 0.0;
   out_6508658752892015980[79] = 0.0;
   out_6508658752892015980[80] = 0.0;
   out_6508658752892015980[81] = 0.0;
   out_6508658752892015980[82] = 0.0;
   out_6508658752892015980[83] = 0.0;
   out_6508658752892015980[84] = 0.0;
   out_6508658752892015980[85] = 0.0;
   out_6508658752892015980[86] = 0.0;
   out_6508658752892015980[87] = 0.0;
   out_6508658752892015980[88] = 0.0;
   out_6508658752892015980[89] = 0.0;
   out_6508658752892015980[90] = 0.0;
   out_6508658752892015980[91] = 0.0;
   out_6508658752892015980[92] = 0.0;
   out_6508658752892015980[93] = 0.0;
   out_6508658752892015980[94] = 0.0;
   out_6508658752892015980[95] = 1.0;
   out_6508658752892015980[96] = 0.0;
   out_6508658752892015980[97] = 0.0;
   out_6508658752892015980[98] = 0.0;
   out_6508658752892015980[99] = 0.0;
   out_6508658752892015980[100] = 0.0;
   out_6508658752892015980[101] = 0.0;
   out_6508658752892015980[102] = 0.0;
   out_6508658752892015980[103] = 0.0;
   out_6508658752892015980[104] = 0.0;
   out_6508658752892015980[105] = 0.0;
   out_6508658752892015980[106] = 0.0;
   out_6508658752892015980[107] = 0.0;
   out_6508658752892015980[108] = 0.0;
   out_6508658752892015980[109] = 0.0;
   out_6508658752892015980[110] = 0.0;
   out_6508658752892015980[111] = 0.0;
   out_6508658752892015980[112] = 0.0;
   out_6508658752892015980[113] = 0.0;
   out_6508658752892015980[114] = 1.0;
   out_6508658752892015980[115] = 0.0;
   out_6508658752892015980[116] = 0.0;
   out_6508658752892015980[117] = 0.0;
   out_6508658752892015980[118] = 0.0;
   out_6508658752892015980[119] = 0.0;
   out_6508658752892015980[120] = 0.0;
   out_6508658752892015980[121] = 0.0;
   out_6508658752892015980[122] = 0.0;
   out_6508658752892015980[123] = 0.0;
   out_6508658752892015980[124] = 0.0;
   out_6508658752892015980[125] = 0.0;
   out_6508658752892015980[126] = 0.0;
   out_6508658752892015980[127] = 0.0;
   out_6508658752892015980[128] = 0.0;
   out_6508658752892015980[129] = 0.0;
   out_6508658752892015980[130] = 0.0;
   out_6508658752892015980[131] = 0.0;
   out_6508658752892015980[132] = 0.0;
   out_6508658752892015980[133] = 1.0;
   out_6508658752892015980[134] = 0.0;
   out_6508658752892015980[135] = 0.0;
   out_6508658752892015980[136] = 0.0;
   out_6508658752892015980[137] = 0.0;
   out_6508658752892015980[138] = 0.0;
   out_6508658752892015980[139] = 0.0;
   out_6508658752892015980[140] = 0.0;
   out_6508658752892015980[141] = 0.0;
   out_6508658752892015980[142] = 0.0;
   out_6508658752892015980[143] = 0.0;
   out_6508658752892015980[144] = 0.0;
   out_6508658752892015980[145] = 0.0;
   out_6508658752892015980[146] = 0.0;
   out_6508658752892015980[147] = 0.0;
   out_6508658752892015980[148] = 0.0;
   out_6508658752892015980[149] = 0.0;
   out_6508658752892015980[150] = 0.0;
   out_6508658752892015980[151] = 0.0;
   out_6508658752892015980[152] = 1.0;
   out_6508658752892015980[153] = 0.0;
   out_6508658752892015980[154] = 0.0;
   out_6508658752892015980[155] = 0.0;
   out_6508658752892015980[156] = 0.0;
   out_6508658752892015980[157] = 0.0;
   out_6508658752892015980[158] = 0.0;
   out_6508658752892015980[159] = 0.0;
   out_6508658752892015980[160] = 0.0;
   out_6508658752892015980[161] = 0.0;
   out_6508658752892015980[162] = 0.0;
   out_6508658752892015980[163] = 0.0;
   out_6508658752892015980[164] = 0.0;
   out_6508658752892015980[165] = 0.0;
   out_6508658752892015980[166] = 0.0;
   out_6508658752892015980[167] = 0.0;
   out_6508658752892015980[168] = 0.0;
   out_6508658752892015980[169] = 0.0;
   out_6508658752892015980[170] = 0.0;
   out_6508658752892015980[171] = 1.0;
   out_6508658752892015980[172] = 0.0;
   out_6508658752892015980[173] = 0.0;
   out_6508658752892015980[174] = 0.0;
   out_6508658752892015980[175] = 0.0;
   out_6508658752892015980[176] = 0.0;
   out_6508658752892015980[177] = 0.0;
   out_6508658752892015980[178] = 0.0;
   out_6508658752892015980[179] = 0.0;
   out_6508658752892015980[180] = 0.0;
   out_6508658752892015980[181] = 0.0;
   out_6508658752892015980[182] = 0.0;
   out_6508658752892015980[183] = 0.0;
   out_6508658752892015980[184] = 0.0;
   out_6508658752892015980[185] = 0.0;
   out_6508658752892015980[186] = 0.0;
   out_6508658752892015980[187] = 0.0;
   out_6508658752892015980[188] = 0.0;
   out_6508658752892015980[189] = 0.0;
   out_6508658752892015980[190] = 1.0;
   out_6508658752892015980[191] = 0.0;
   out_6508658752892015980[192] = 0.0;
   out_6508658752892015980[193] = 0.0;
   out_6508658752892015980[194] = 0.0;
   out_6508658752892015980[195] = 0.0;
   out_6508658752892015980[196] = 0.0;
   out_6508658752892015980[197] = 0.0;
   out_6508658752892015980[198] = 0.0;
   out_6508658752892015980[199] = 0.0;
   out_6508658752892015980[200] = 0.0;
   out_6508658752892015980[201] = 0.0;
   out_6508658752892015980[202] = 0.0;
   out_6508658752892015980[203] = 0.0;
   out_6508658752892015980[204] = 0.0;
   out_6508658752892015980[205] = 0.0;
   out_6508658752892015980[206] = 0.0;
   out_6508658752892015980[207] = 0.0;
   out_6508658752892015980[208] = 0.0;
   out_6508658752892015980[209] = 1.0;
   out_6508658752892015980[210] = 0.0;
   out_6508658752892015980[211] = 0.0;
   out_6508658752892015980[212] = 0.0;
   out_6508658752892015980[213] = 0.0;
   out_6508658752892015980[214] = 0.0;
   out_6508658752892015980[215] = 0.0;
   out_6508658752892015980[216] = 0.0;
   out_6508658752892015980[217] = 0.0;
   out_6508658752892015980[218] = 0.0;
   out_6508658752892015980[219] = 0.0;
   out_6508658752892015980[220] = 0.0;
   out_6508658752892015980[221] = 0.0;
   out_6508658752892015980[222] = 0.0;
   out_6508658752892015980[223] = 0.0;
   out_6508658752892015980[224] = 0.0;
   out_6508658752892015980[225] = 0.0;
   out_6508658752892015980[226] = 0.0;
   out_6508658752892015980[227] = 0.0;
   out_6508658752892015980[228] = 1.0;
   out_6508658752892015980[229] = 0.0;
   out_6508658752892015980[230] = 0.0;
   out_6508658752892015980[231] = 0.0;
   out_6508658752892015980[232] = 0.0;
   out_6508658752892015980[233] = 0.0;
   out_6508658752892015980[234] = 0.0;
   out_6508658752892015980[235] = 0.0;
   out_6508658752892015980[236] = 0.0;
   out_6508658752892015980[237] = 0.0;
   out_6508658752892015980[238] = 0.0;
   out_6508658752892015980[239] = 0.0;
   out_6508658752892015980[240] = 0.0;
   out_6508658752892015980[241] = 0.0;
   out_6508658752892015980[242] = 0.0;
   out_6508658752892015980[243] = 0.0;
   out_6508658752892015980[244] = 0.0;
   out_6508658752892015980[245] = 0.0;
   out_6508658752892015980[246] = 0.0;
   out_6508658752892015980[247] = 1.0;
   out_6508658752892015980[248] = 0.0;
   out_6508658752892015980[249] = 0.0;
   out_6508658752892015980[250] = 0.0;
   out_6508658752892015980[251] = 0.0;
   out_6508658752892015980[252] = 0.0;
   out_6508658752892015980[253] = 0.0;
   out_6508658752892015980[254] = 0.0;
   out_6508658752892015980[255] = 0.0;
   out_6508658752892015980[256] = 0.0;
   out_6508658752892015980[257] = 0.0;
   out_6508658752892015980[258] = 0.0;
   out_6508658752892015980[259] = 0.0;
   out_6508658752892015980[260] = 0.0;
   out_6508658752892015980[261] = 0.0;
   out_6508658752892015980[262] = 0.0;
   out_6508658752892015980[263] = 0.0;
   out_6508658752892015980[264] = 0.0;
   out_6508658752892015980[265] = 0.0;
   out_6508658752892015980[266] = 1.0;
   out_6508658752892015980[267] = 0.0;
   out_6508658752892015980[268] = 0.0;
   out_6508658752892015980[269] = 0.0;
   out_6508658752892015980[270] = 0.0;
   out_6508658752892015980[271] = 0.0;
   out_6508658752892015980[272] = 0.0;
   out_6508658752892015980[273] = 0.0;
   out_6508658752892015980[274] = 0.0;
   out_6508658752892015980[275] = 0.0;
   out_6508658752892015980[276] = 0.0;
   out_6508658752892015980[277] = 0.0;
   out_6508658752892015980[278] = 0.0;
   out_6508658752892015980[279] = 0.0;
   out_6508658752892015980[280] = 0.0;
   out_6508658752892015980[281] = 0.0;
   out_6508658752892015980[282] = 0.0;
   out_6508658752892015980[283] = 0.0;
   out_6508658752892015980[284] = 0.0;
   out_6508658752892015980[285] = 1.0;
   out_6508658752892015980[286] = 0.0;
   out_6508658752892015980[287] = 0.0;
   out_6508658752892015980[288] = 0.0;
   out_6508658752892015980[289] = 0.0;
   out_6508658752892015980[290] = 0.0;
   out_6508658752892015980[291] = 0.0;
   out_6508658752892015980[292] = 0.0;
   out_6508658752892015980[293] = 0.0;
   out_6508658752892015980[294] = 0.0;
   out_6508658752892015980[295] = 0.0;
   out_6508658752892015980[296] = 0.0;
   out_6508658752892015980[297] = 0.0;
   out_6508658752892015980[298] = 0.0;
   out_6508658752892015980[299] = 0.0;
   out_6508658752892015980[300] = 0.0;
   out_6508658752892015980[301] = 0.0;
   out_6508658752892015980[302] = 0.0;
   out_6508658752892015980[303] = 0.0;
   out_6508658752892015980[304] = 1.0;
   out_6508658752892015980[305] = 0.0;
   out_6508658752892015980[306] = 0.0;
   out_6508658752892015980[307] = 0.0;
   out_6508658752892015980[308] = 0.0;
   out_6508658752892015980[309] = 0.0;
   out_6508658752892015980[310] = 0.0;
   out_6508658752892015980[311] = 0.0;
   out_6508658752892015980[312] = 0.0;
   out_6508658752892015980[313] = 0.0;
   out_6508658752892015980[314] = 0.0;
   out_6508658752892015980[315] = 0.0;
   out_6508658752892015980[316] = 0.0;
   out_6508658752892015980[317] = 0.0;
   out_6508658752892015980[318] = 0.0;
   out_6508658752892015980[319] = 0.0;
   out_6508658752892015980[320] = 0.0;
   out_6508658752892015980[321] = 0.0;
   out_6508658752892015980[322] = 0.0;
   out_6508658752892015980[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_7991760748331142667) {
   out_7991760748331142667[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_7991760748331142667[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_7991760748331142667[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_7991760748331142667[3] = dt*state[12] + state[3];
   out_7991760748331142667[4] = dt*state[13] + state[4];
   out_7991760748331142667[5] = dt*state[14] + state[5];
   out_7991760748331142667[6] = state[6];
   out_7991760748331142667[7] = state[7];
   out_7991760748331142667[8] = state[8];
   out_7991760748331142667[9] = state[9];
   out_7991760748331142667[10] = state[10];
   out_7991760748331142667[11] = state[11];
   out_7991760748331142667[12] = state[12];
   out_7991760748331142667[13] = state[13];
   out_7991760748331142667[14] = state[14];
   out_7991760748331142667[15] = state[15];
   out_7991760748331142667[16] = state[16];
   out_7991760748331142667[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2236499869103053430) {
   out_2236499869103053430[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2236499869103053430[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2236499869103053430[2] = 0;
   out_2236499869103053430[3] = 0;
   out_2236499869103053430[4] = 0;
   out_2236499869103053430[5] = 0;
   out_2236499869103053430[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2236499869103053430[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2236499869103053430[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2236499869103053430[9] = 0;
   out_2236499869103053430[10] = 0;
   out_2236499869103053430[11] = 0;
   out_2236499869103053430[12] = 0;
   out_2236499869103053430[13] = 0;
   out_2236499869103053430[14] = 0;
   out_2236499869103053430[15] = 0;
   out_2236499869103053430[16] = 0;
   out_2236499869103053430[17] = 0;
   out_2236499869103053430[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2236499869103053430[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2236499869103053430[20] = 0;
   out_2236499869103053430[21] = 0;
   out_2236499869103053430[22] = 0;
   out_2236499869103053430[23] = 0;
   out_2236499869103053430[24] = 0;
   out_2236499869103053430[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2236499869103053430[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2236499869103053430[27] = 0;
   out_2236499869103053430[28] = 0;
   out_2236499869103053430[29] = 0;
   out_2236499869103053430[30] = 0;
   out_2236499869103053430[31] = 0;
   out_2236499869103053430[32] = 0;
   out_2236499869103053430[33] = 0;
   out_2236499869103053430[34] = 0;
   out_2236499869103053430[35] = 0;
   out_2236499869103053430[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2236499869103053430[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2236499869103053430[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2236499869103053430[39] = 0;
   out_2236499869103053430[40] = 0;
   out_2236499869103053430[41] = 0;
   out_2236499869103053430[42] = 0;
   out_2236499869103053430[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2236499869103053430[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2236499869103053430[45] = 0;
   out_2236499869103053430[46] = 0;
   out_2236499869103053430[47] = 0;
   out_2236499869103053430[48] = 0;
   out_2236499869103053430[49] = 0;
   out_2236499869103053430[50] = 0;
   out_2236499869103053430[51] = 0;
   out_2236499869103053430[52] = 0;
   out_2236499869103053430[53] = 0;
   out_2236499869103053430[54] = 0;
   out_2236499869103053430[55] = 0;
   out_2236499869103053430[56] = 0;
   out_2236499869103053430[57] = 1;
   out_2236499869103053430[58] = 0;
   out_2236499869103053430[59] = 0;
   out_2236499869103053430[60] = 0;
   out_2236499869103053430[61] = 0;
   out_2236499869103053430[62] = 0;
   out_2236499869103053430[63] = 0;
   out_2236499869103053430[64] = 0;
   out_2236499869103053430[65] = 0;
   out_2236499869103053430[66] = dt;
   out_2236499869103053430[67] = 0;
   out_2236499869103053430[68] = 0;
   out_2236499869103053430[69] = 0;
   out_2236499869103053430[70] = 0;
   out_2236499869103053430[71] = 0;
   out_2236499869103053430[72] = 0;
   out_2236499869103053430[73] = 0;
   out_2236499869103053430[74] = 0;
   out_2236499869103053430[75] = 0;
   out_2236499869103053430[76] = 1;
   out_2236499869103053430[77] = 0;
   out_2236499869103053430[78] = 0;
   out_2236499869103053430[79] = 0;
   out_2236499869103053430[80] = 0;
   out_2236499869103053430[81] = 0;
   out_2236499869103053430[82] = 0;
   out_2236499869103053430[83] = 0;
   out_2236499869103053430[84] = 0;
   out_2236499869103053430[85] = dt;
   out_2236499869103053430[86] = 0;
   out_2236499869103053430[87] = 0;
   out_2236499869103053430[88] = 0;
   out_2236499869103053430[89] = 0;
   out_2236499869103053430[90] = 0;
   out_2236499869103053430[91] = 0;
   out_2236499869103053430[92] = 0;
   out_2236499869103053430[93] = 0;
   out_2236499869103053430[94] = 0;
   out_2236499869103053430[95] = 1;
   out_2236499869103053430[96] = 0;
   out_2236499869103053430[97] = 0;
   out_2236499869103053430[98] = 0;
   out_2236499869103053430[99] = 0;
   out_2236499869103053430[100] = 0;
   out_2236499869103053430[101] = 0;
   out_2236499869103053430[102] = 0;
   out_2236499869103053430[103] = 0;
   out_2236499869103053430[104] = dt;
   out_2236499869103053430[105] = 0;
   out_2236499869103053430[106] = 0;
   out_2236499869103053430[107] = 0;
   out_2236499869103053430[108] = 0;
   out_2236499869103053430[109] = 0;
   out_2236499869103053430[110] = 0;
   out_2236499869103053430[111] = 0;
   out_2236499869103053430[112] = 0;
   out_2236499869103053430[113] = 0;
   out_2236499869103053430[114] = 1;
   out_2236499869103053430[115] = 0;
   out_2236499869103053430[116] = 0;
   out_2236499869103053430[117] = 0;
   out_2236499869103053430[118] = 0;
   out_2236499869103053430[119] = 0;
   out_2236499869103053430[120] = 0;
   out_2236499869103053430[121] = 0;
   out_2236499869103053430[122] = 0;
   out_2236499869103053430[123] = 0;
   out_2236499869103053430[124] = 0;
   out_2236499869103053430[125] = 0;
   out_2236499869103053430[126] = 0;
   out_2236499869103053430[127] = 0;
   out_2236499869103053430[128] = 0;
   out_2236499869103053430[129] = 0;
   out_2236499869103053430[130] = 0;
   out_2236499869103053430[131] = 0;
   out_2236499869103053430[132] = 0;
   out_2236499869103053430[133] = 1;
   out_2236499869103053430[134] = 0;
   out_2236499869103053430[135] = 0;
   out_2236499869103053430[136] = 0;
   out_2236499869103053430[137] = 0;
   out_2236499869103053430[138] = 0;
   out_2236499869103053430[139] = 0;
   out_2236499869103053430[140] = 0;
   out_2236499869103053430[141] = 0;
   out_2236499869103053430[142] = 0;
   out_2236499869103053430[143] = 0;
   out_2236499869103053430[144] = 0;
   out_2236499869103053430[145] = 0;
   out_2236499869103053430[146] = 0;
   out_2236499869103053430[147] = 0;
   out_2236499869103053430[148] = 0;
   out_2236499869103053430[149] = 0;
   out_2236499869103053430[150] = 0;
   out_2236499869103053430[151] = 0;
   out_2236499869103053430[152] = 1;
   out_2236499869103053430[153] = 0;
   out_2236499869103053430[154] = 0;
   out_2236499869103053430[155] = 0;
   out_2236499869103053430[156] = 0;
   out_2236499869103053430[157] = 0;
   out_2236499869103053430[158] = 0;
   out_2236499869103053430[159] = 0;
   out_2236499869103053430[160] = 0;
   out_2236499869103053430[161] = 0;
   out_2236499869103053430[162] = 0;
   out_2236499869103053430[163] = 0;
   out_2236499869103053430[164] = 0;
   out_2236499869103053430[165] = 0;
   out_2236499869103053430[166] = 0;
   out_2236499869103053430[167] = 0;
   out_2236499869103053430[168] = 0;
   out_2236499869103053430[169] = 0;
   out_2236499869103053430[170] = 0;
   out_2236499869103053430[171] = 1;
   out_2236499869103053430[172] = 0;
   out_2236499869103053430[173] = 0;
   out_2236499869103053430[174] = 0;
   out_2236499869103053430[175] = 0;
   out_2236499869103053430[176] = 0;
   out_2236499869103053430[177] = 0;
   out_2236499869103053430[178] = 0;
   out_2236499869103053430[179] = 0;
   out_2236499869103053430[180] = 0;
   out_2236499869103053430[181] = 0;
   out_2236499869103053430[182] = 0;
   out_2236499869103053430[183] = 0;
   out_2236499869103053430[184] = 0;
   out_2236499869103053430[185] = 0;
   out_2236499869103053430[186] = 0;
   out_2236499869103053430[187] = 0;
   out_2236499869103053430[188] = 0;
   out_2236499869103053430[189] = 0;
   out_2236499869103053430[190] = 1;
   out_2236499869103053430[191] = 0;
   out_2236499869103053430[192] = 0;
   out_2236499869103053430[193] = 0;
   out_2236499869103053430[194] = 0;
   out_2236499869103053430[195] = 0;
   out_2236499869103053430[196] = 0;
   out_2236499869103053430[197] = 0;
   out_2236499869103053430[198] = 0;
   out_2236499869103053430[199] = 0;
   out_2236499869103053430[200] = 0;
   out_2236499869103053430[201] = 0;
   out_2236499869103053430[202] = 0;
   out_2236499869103053430[203] = 0;
   out_2236499869103053430[204] = 0;
   out_2236499869103053430[205] = 0;
   out_2236499869103053430[206] = 0;
   out_2236499869103053430[207] = 0;
   out_2236499869103053430[208] = 0;
   out_2236499869103053430[209] = 1;
   out_2236499869103053430[210] = 0;
   out_2236499869103053430[211] = 0;
   out_2236499869103053430[212] = 0;
   out_2236499869103053430[213] = 0;
   out_2236499869103053430[214] = 0;
   out_2236499869103053430[215] = 0;
   out_2236499869103053430[216] = 0;
   out_2236499869103053430[217] = 0;
   out_2236499869103053430[218] = 0;
   out_2236499869103053430[219] = 0;
   out_2236499869103053430[220] = 0;
   out_2236499869103053430[221] = 0;
   out_2236499869103053430[222] = 0;
   out_2236499869103053430[223] = 0;
   out_2236499869103053430[224] = 0;
   out_2236499869103053430[225] = 0;
   out_2236499869103053430[226] = 0;
   out_2236499869103053430[227] = 0;
   out_2236499869103053430[228] = 1;
   out_2236499869103053430[229] = 0;
   out_2236499869103053430[230] = 0;
   out_2236499869103053430[231] = 0;
   out_2236499869103053430[232] = 0;
   out_2236499869103053430[233] = 0;
   out_2236499869103053430[234] = 0;
   out_2236499869103053430[235] = 0;
   out_2236499869103053430[236] = 0;
   out_2236499869103053430[237] = 0;
   out_2236499869103053430[238] = 0;
   out_2236499869103053430[239] = 0;
   out_2236499869103053430[240] = 0;
   out_2236499869103053430[241] = 0;
   out_2236499869103053430[242] = 0;
   out_2236499869103053430[243] = 0;
   out_2236499869103053430[244] = 0;
   out_2236499869103053430[245] = 0;
   out_2236499869103053430[246] = 0;
   out_2236499869103053430[247] = 1;
   out_2236499869103053430[248] = 0;
   out_2236499869103053430[249] = 0;
   out_2236499869103053430[250] = 0;
   out_2236499869103053430[251] = 0;
   out_2236499869103053430[252] = 0;
   out_2236499869103053430[253] = 0;
   out_2236499869103053430[254] = 0;
   out_2236499869103053430[255] = 0;
   out_2236499869103053430[256] = 0;
   out_2236499869103053430[257] = 0;
   out_2236499869103053430[258] = 0;
   out_2236499869103053430[259] = 0;
   out_2236499869103053430[260] = 0;
   out_2236499869103053430[261] = 0;
   out_2236499869103053430[262] = 0;
   out_2236499869103053430[263] = 0;
   out_2236499869103053430[264] = 0;
   out_2236499869103053430[265] = 0;
   out_2236499869103053430[266] = 1;
   out_2236499869103053430[267] = 0;
   out_2236499869103053430[268] = 0;
   out_2236499869103053430[269] = 0;
   out_2236499869103053430[270] = 0;
   out_2236499869103053430[271] = 0;
   out_2236499869103053430[272] = 0;
   out_2236499869103053430[273] = 0;
   out_2236499869103053430[274] = 0;
   out_2236499869103053430[275] = 0;
   out_2236499869103053430[276] = 0;
   out_2236499869103053430[277] = 0;
   out_2236499869103053430[278] = 0;
   out_2236499869103053430[279] = 0;
   out_2236499869103053430[280] = 0;
   out_2236499869103053430[281] = 0;
   out_2236499869103053430[282] = 0;
   out_2236499869103053430[283] = 0;
   out_2236499869103053430[284] = 0;
   out_2236499869103053430[285] = 1;
   out_2236499869103053430[286] = 0;
   out_2236499869103053430[287] = 0;
   out_2236499869103053430[288] = 0;
   out_2236499869103053430[289] = 0;
   out_2236499869103053430[290] = 0;
   out_2236499869103053430[291] = 0;
   out_2236499869103053430[292] = 0;
   out_2236499869103053430[293] = 0;
   out_2236499869103053430[294] = 0;
   out_2236499869103053430[295] = 0;
   out_2236499869103053430[296] = 0;
   out_2236499869103053430[297] = 0;
   out_2236499869103053430[298] = 0;
   out_2236499869103053430[299] = 0;
   out_2236499869103053430[300] = 0;
   out_2236499869103053430[301] = 0;
   out_2236499869103053430[302] = 0;
   out_2236499869103053430[303] = 0;
   out_2236499869103053430[304] = 1;
   out_2236499869103053430[305] = 0;
   out_2236499869103053430[306] = 0;
   out_2236499869103053430[307] = 0;
   out_2236499869103053430[308] = 0;
   out_2236499869103053430[309] = 0;
   out_2236499869103053430[310] = 0;
   out_2236499869103053430[311] = 0;
   out_2236499869103053430[312] = 0;
   out_2236499869103053430[313] = 0;
   out_2236499869103053430[314] = 0;
   out_2236499869103053430[315] = 0;
   out_2236499869103053430[316] = 0;
   out_2236499869103053430[317] = 0;
   out_2236499869103053430[318] = 0;
   out_2236499869103053430[319] = 0;
   out_2236499869103053430[320] = 0;
   out_2236499869103053430[321] = 0;
   out_2236499869103053430[322] = 0;
   out_2236499869103053430[323] = 1;
}
void h_4(double *state, double *unused, double *out_8843213748921434845) {
   out_8843213748921434845[0] = state[6] + state[9];
   out_8843213748921434845[1] = state[7] + state[10];
   out_8843213748921434845[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3234436674101066727) {
   out_3234436674101066727[0] = 0;
   out_3234436674101066727[1] = 0;
   out_3234436674101066727[2] = 0;
   out_3234436674101066727[3] = 0;
   out_3234436674101066727[4] = 0;
   out_3234436674101066727[5] = 0;
   out_3234436674101066727[6] = 1;
   out_3234436674101066727[7] = 0;
   out_3234436674101066727[8] = 0;
   out_3234436674101066727[9] = 1;
   out_3234436674101066727[10] = 0;
   out_3234436674101066727[11] = 0;
   out_3234436674101066727[12] = 0;
   out_3234436674101066727[13] = 0;
   out_3234436674101066727[14] = 0;
   out_3234436674101066727[15] = 0;
   out_3234436674101066727[16] = 0;
   out_3234436674101066727[17] = 0;
   out_3234436674101066727[18] = 0;
   out_3234436674101066727[19] = 0;
   out_3234436674101066727[20] = 0;
   out_3234436674101066727[21] = 0;
   out_3234436674101066727[22] = 0;
   out_3234436674101066727[23] = 0;
   out_3234436674101066727[24] = 0;
   out_3234436674101066727[25] = 1;
   out_3234436674101066727[26] = 0;
   out_3234436674101066727[27] = 0;
   out_3234436674101066727[28] = 1;
   out_3234436674101066727[29] = 0;
   out_3234436674101066727[30] = 0;
   out_3234436674101066727[31] = 0;
   out_3234436674101066727[32] = 0;
   out_3234436674101066727[33] = 0;
   out_3234436674101066727[34] = 0;
   out_3234436674101066727[35] = 0;
   out_3234436674101066727[36] = 0;
   out_3234436674101066727[37] = 0;
   out_3234436674101066727[38] = 0;
   out_3234436674101066727[39] = 0;
   out_3234436674101066727[40] = 0;
   out_3234436674101066727[41] = 0;
   out_3234436674101066727[42] = 0;
   out_3234436674101066727[43] = 0;
   out_3234436674101066727[44] = 1;
   out_3234436674101066727[45] = 0;
   out_3234436674101066727[46] = 0;
   out_3234436674101066727[47] = 1;
   out_3234436674101066727[48] = 0;
   out_3234436674101066727[49] = 0;
   out_3234436674101066727[50] = 0;
   out_3234436674101066727[51] = 0;
   out_3234436674101066727[52] = 0;
   out_3234436674101066727[53] = 0;
}
void h_10(double *state, double *unused, double *out_3208643256414619500) {
   out_3208643256414619500[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3208643256414619500[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3208643256414619500[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6406759991116077694) {
   out_6406759991116077694[0] = 0;
   out_6406759991116077694[1] = 9.8100000000000005*cos(state[1]);
   out_6406759991116077694[2] = 0;
   out_6406759991116077694[3] = 0;
   out_6406759991116077694[4] = -state[8];
   out_6406759991116077694[5] = state[7];
   out_6406759991116077694[6] = 0;
   out_6406759991116077694[7] = state[5];
   out_6406759991116077694[8] = -state[4];
   out_6406759991116077694[9] = 0;
   out_6406759991116077694[10] = 0;
   out_6406759991116077694[11] = 0;
   out_6406759991116077694[12] = 1;
   out_6406759991116077694[13] = 0;
   out_6406759991116077694[14] = 0;
   out_6406759991116077694[15] = 1;
   out_6406759991116077694[16] = 0;
   out_6406759991116077694[17] = 0;
   out_6406759991116077694[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6406759991116077694[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6406759991116077694[20] = 0;
   out_6406759991116077694[21] = state[8];
   out_6406759991116077694[22] = 0;
   out_6406759991116077694[23] = -state[6];
   out_6406759991116077694[24] = -state[5];
   out_6406759991116077694[25] = 0;
   out_6406759991116077694[26] = state[3];
   out_6406759991116077694[27] = 0;
   out_6406759991116077694[28] = 0;
   out_6406759991116077694[29] = 0;
   out_6406759991116077694[30] = 0;
   out_6406759991116077694[31] = 1;
   out_6406759991116077694[32] = 0;
   out_6406759991116077694[33] = 0;
   out_6406759991116077694[34] = 1;
   out_6406759991116077694[35] = 0;
   out_6406759991116077694[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6406759991116077694[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6406759991116077694[38] = 0;
   out_6406759991116077694[39] = -state[7];
   out_6406759991116077694[40] = state[6];
   out_6406759991116077694[41] = 0;
   out_6406759991116077694[42] = state[4];
   out_6406759991116077694[43] = -state[3];
   out_6406759991116077694[44] = 0;
   out_6406759991116077694[45] = 0;
   out_6406759991116077694[46] = 0;
   out_6406759991116077694[47] = 0;
   out_6406759991116077694[48] = 0;
   out_6406759991116077694[49] = 0;
   out_6406759991116077694[50] = 1;
   out_6406759991116077694[51] = 0;
   out_6406759991116077694[52] = 0;
   out_6406759991116077694[53] = 1;
}
void h_13(double *state, double *unused, double *out_7275462902737089254) {
   out_7275462902737089254[0] = state[3];
   out_7275462902737089254[1] = state[4];
   out_7275462902737089254[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6446710499433399528) {
   out_6446710499433399528[0] = 0;
   out_6446710499433399528[1] = 0;
   out_6446710499433399528[2] = 0;
   out_6446710499433399528[3] = 1;
   out_6446710499433399528[4] = 0;
   out_6446710499433399528[5] = 0;
   out_6446710499433399528[6] = 0;
   out_6446710499433399528[7] = 0;
   out_6446710499433399528[8] = 0;
   out_6446710499433399528[9] = 0;
   out_6446710499433399528[10] = 0;
   out_6446710499433399528[11] = 0;
   out_6446710499433399528[12] = 0;
   out_6446710499433399528[13] = 0;
   out_6446710499433399528[14] = 0;
   out_6446710499433399528[15] = 0;
   out_6446710499433399528[16] = 0;
   out_6446710499433399528[17] = 0;
   out_6446710499433399528[18] = 0;
   out_6446710499433399528[19] = 0;
   out_6446710499433399528[20] = 0;
   out_6446710499433399528[21] = 0;
   out_6446710499433399528[22] = 1;
   out_6446710499433399528[23] = 0;
   out_6446710499433399528[24] = 0;
   out_6446710499433399528[25] = 0;
   out_6446710499433399528[26] = 0;
   out_6446710499433399528[27] = 0;
   out_6446710499433399528[28] = 0;
   out_6446710499433399528[29] = 0;
   out_6446710499433399528[30] = 0;
   out_6446710499433399528[31] = 0;
   out_6446710499433399528[32] = 0;
   out_6446710499433399528[33] = 0;
   out_6446710499433399528[34] = 0;
   out_6446710499433399528[35] = 0;
   out_6446710499433399528[36] = 0;
   out_6446710499433399528[37] = 0;
   out_6446710499433399528[38] = 0;
   out_6446710499433399528[39] = 0;
   out_6446710499433399528[40] = 0;
   out_6446710499433399528[41] = 1;
   out_6446710499433399528[42] = 0;
   out_6446710499433399528[43] = 0;
   out_6446710499433399528[44] = 0;
   out_6446710499433399528[45] = 0;
   out_6446710499433399528[46] = 0;
   out_6446710499433399528[47] = 0;
   out_6446710499433399528[48] = 0;
   out_6446710499433399528[49] = 0;
   out_6446710499433399528[50] = 0;
   out_6446710499433399528[51] = 0;
   out_6446710499433399528[52] = 0;
   out_6446710499433399528[53] = 0;
}
void h_14(double *state, double *unused, double *out_3384719431142301101) {
   out_3384719431142301101[0] = state[6];
   out_3384719431142301101[1] = state[7];
   out_3384719431142301101[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7197677530440551256) {
   out_7197677530440551256[0] = 0;
   out_7197677530440551256[1] = 0;
   out_7197677530440551256[2] = 0;
   out_7197677530440551256[3] = 0;
   out_7197677530440551256[4] = 0;
   out_7197677530440551256[5] = 0;
   out_7197677530440551256[6] = 1;
   out_7197677530440551256[7] = 0;
   out_7197677530440551256[8] = 0;
   out_7197677530440551256[9] = 0;
   out_7197677530440551256[10] = 0;
   out_7197677530440551256[11] = 0;
   out_7197677530440551256[12] = 0;
   out_7197677530440551256[13] = 0;
   out_7197677530440551256[14] = 0;
   out_7197677530440551256[15] = 0;
   out_7197677530440551256[16] = 0;
   out_7197677530440551256[17] = 0;
   out_7197677530440551256[18] = 0;
   out_7197677530440551256[19] = 0;
   out_7197677530440551256[20] = 0;
   out_7197677530440551256[21] = 0;
   out_7197677530440551256[22] = 0;
   out_7197677530440551256[23] = 0;
   out_7197677530440551256[24] = 0;
   out_7197677530440551256[25] = 1;
   out_7197677530440551256[26] = 0;
   out_7197677530440551256[27] = 0;
   out_7197677530440551256[28] = 0;
   out_7197677530440551256[29] = 0;
   out_7197677530440551256[30] = 0;
   out_7197677530440551256[31] = 0;
   out_7197677530440551256[32] = 0;
   out_7197677530440551256[33] = 0;
   out_7197677530440551256[34] = 0;
   out_7197677530440551256[35] = 0;
   out_7197677530440551256[36] = 0;
   out_7197677530440551256[37] = 0;
   out_7197677530440551256[38] = 0;
   out_7197677530440551256[39] = 0;
   out_7197677530440551256[40] = 0;
   out_7197677530440551256[41] = 0;
   out_7197677530440551256[42] = 0;
   out_7197677530440551256[43] = 0;
   out_7197677530440551256[44] = 1;
   out_7197677530440551256[45] = 0;
   out_7197677530440551256[46] = 0;
   out_7197677530440551256[47] = 0;
   out_7197677530440551256[48] = 0;
   out_7197677530440551256[49] = 0;
   out_7197677530440551256[50] = 0;
   out_7197677530440551256[51] = 0;
   out_7197677530440551256[52] = 0;
   out_7197677530440551256[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3784924644306313628) {
  err_fun(nom_x, delta_x, out_3784924644306313628);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_540309216742292633) {
  inv_err_fun(nom_x, true_x, out_540309216742292633);
}
void pose_H_mod_fun(double *state, double *out_6508658752892015980) {
  H_mod_fun(state, out_6508658752892015980);
}
void pose_f_fun(double *state, double dt, double *out_7991760748331142667) {
  f_fun(state,  dt, out_7991760748331142667);
}
void pose_F_fun(double *state, double dt, double *out_2236499869103053430) {
  F_fun(state,  dt, out_2236499869103053430);
}
void pose_h_4(double *state, double *unused, double *out_8843213748921434845) {
  h_4(state, unused, out_8843213748921434845);
}
void pose_H_4(double *state, double *unused, double *out_3234436674101066727) {
  H_4(state, unused, out_3234436674101066727);
}
void pose_h_10(double *state, double *unused, double *out_3208643256414619500) {
  h_10(state, unused, out_3208643256414619500);
}
void pose_H_10(double *state, double *unused, double *out_6406759991116077694) {
  H_10(state, unused, out_6406759991116077694);
}
void pose_h_13(double *state, double *unused, double *out_7275462902737089254) {
  h_13(state, unused, out_7275462902737089254);
}
void pose_H_13(double *state, double *unused, double *out_6446710499433399528) {
  H_13(state, unused, out_6446710499433399528);
}
void pose_h_14(double *state, double *unused, double *out_3384719431142301101) {
  h_14(state, unused, out_3384719431142301101);
}
void pose_H_14(double *state, double *unused, double *out_7197677530440551256) {
  H_14(state, unused, out_7197677530440551256);
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
