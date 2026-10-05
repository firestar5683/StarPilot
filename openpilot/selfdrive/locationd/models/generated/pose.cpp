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
void err_fun(double *nom_x, double *delta_x, double *out_1686705028277529867) {
   out_1686705028277529867[0] = delta_x[0] + nom_x[0];
   out_1686705028277529867[1] = delta_x[1] + nom_x[1];
   out_1686705028277529867[2] = delta_x[2] + nom_x[2];
   out_1686705028277529867[3] = delta_x[3] + nom_x[3];
   out_1686705028277529867[4] = delta_x[4] + nom_x[4];
   out_1686705028277529867[5] = delta_x[5] + nom_x[5];
   out_1686705028277529867[6] = delta_x[6] + nom_x[6];
   out_1686705028277529867[7] = delta_x[7] + nom_x[7];
   out_1686705028277529867[8] = delta_x[8] + nom_x[8];
   out_1686705028277529867[9] = delta_x[9] + nom_x[9];
   out_1686705028277529867[10] = delta_x[10] + nom_x[10];
   out_1686705028277529867[11] = delta_x[11] + nom_x[11];
   out_1686705028277529867[12] = delta_x[12] + nom_x[12];
   out_1686705028277529867[13] = delta_x[13] + nom_x[13];
   out_1686705028277529867[14] = delta_x[14] + nom_x[14];
   out_1686705028277529867[15] = delta_x[15] + nom_x[15];
   out_1686705028277529867[16] = delta_x[16] + nom_x[16];
   out_1686705028277529867[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1103979266905204510) {
   out_1103979266905204510[0] = -nom_x[0] + true_x[0];
   out_1103979266905204510[1] = -nom_x[1] + true_x[1];
   out_1103979266905204510[2] = -nom_x[2] + true_x[2];
   out_1103979266905204510[3] = -nom_x[3] + true_x[3];
   out_1103979266905204510[4] = -nom_x[4] + true_x[4];
   out_1103979266905204510[5] = -nom_x[5] + true_x[5];
   out_1103979266905204510[6] = -nom_x[6] + true_x[6];
   out_1103979266905204510[7] = -nom_x[7] + true_x[7];
   out_1103979266905204510[8] = -nom_x[8] + true_x[8];
   out_1103979266905204510[9] = -nom_x[9] + true_x[9];
   out_1103979266905204510[10] = -nom_x[10] + true_x[10];
   out_1103979266905204510[11] = -nom_x[11] + true_x[11];
   out_1103979266905204510[12] = -nom_x[12] + true_x[12];
   out_1103979266905204510[13] = -nom_x[13] + true_x[13];
   out_1103979266905204510[14] = -nom_x[14] + true_x[14];
   out_1103979266905204510[15] = -nom_x[15] + true_x[15];
   out_1103979266905204510[16] = -nom_x[16] + true_x[16];
   out_1103979266905204510[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3778009894403191156) {
   out_3778009894403191156[0] = 1.0;
   out_3778009894403191156[1] = 0.0;
   out_3778009894403191156[2] = 0.0;
   out_3778009894403191156[3] = 0.0;
   out_3778009894403191156[4] = 0.0;
   out_3778009894403191156[5] = 0.0;
   out_3778009894403191156[6] = 0.0;
   out_3778009894403191156[7] = 0.0;
   out_3778009894403191156[8] = 0.0;
   out_3778009894403191156[9] = 0.0;
   out_3778009894403191156[10] = 0.0;
   out_3778009894403191156[11] = 0.0;
   out_3778009894403191156[12] = 0.0;
   out_3778009894403191156[13] = 0.0;
   out_3778009894403191156[14] = 0.0;
   out_3778009894403191156[15] = 0.0;
   out_3778009894403191156[16] = 0.0;
   out_3778009894403191156[17] = 0.0;
   out_3778009894403191156[18] = 0.0;
   out_3778009894403191156[19] = 1.0;
   out_3778009894403191156[20] = 0.0;
   out_3778009894403191156[21] = 0.0;
   out_3778009894403191156[22] = 0.0;
   out_3778009894403191156[23] = 0.0;
   out_3778009894403191156[24] = 0.0;
   out_3778009894403191156[25] = 0.0;
   out_3778009894403191156[26] = 0.0;
   out_3778009894403191156[27] = 0.0;
   out_3778009894403191156[28] = 0.0;
   out_3778009894403191156[29] = 0.0;
   out_3778009894403191156[30] = 0.0;
   out_3778009894403191156[31] = 0.0;
   out_3778009894403191156[32] = 0.0;
   out_3778009894403191156[33] = 0.0;
   out_3778009894403191156[34] = 0.0;
   out_3778009894403191156[35] = 0.0;
   out_3778009894403191156[36] = 0.0;
   out_3778009894403191156[37] = 0.0;
   out_3778009894403191156[38] = 1.0;
   out_3778009894403191156[39] = 0.0;
   out_3778009894403191156[40] = 0.0;
   out_3778009894403191156[41] = 0.0;
   out_3778009894403191156[42] = 0.0;
   out_3778009894403191156[43] = 0.0;
   out_3778009894403191156[44] = 0.0;
   out_3778009894403191156[45] = 0.0;
   out_3778009894403191156[46] = 0.0;
   out_3778009894403191156[47] = 0.0;
   out_3778009894403191156[48] = 0.0;
   out_3778009894403191156[49] = 0.0;
   out_3778009894403191156[50] = 0.0;
   out_3778009894403191156[51] = 0.0;
   out_3778009894403191156[52] = 0.0;
   out_3778009894403191156[53] = 0.0;
   out_3778009894403191156[54] = 0.0;
   out_3778009894403191156[55] = 0.0;
   out_3778009894403191156[56] = 0.0;
   out_3778009894403191156[57] = 1.0;
   out_3778009894403191156[58] = 0.0;
   out_3778009894403191156[59] = 0.0;
   out_3778009894403191156[60] = 0.0;
   out_3778009894403191156[61] = 0.0;
   out_3778009894403191156[62] = 0.0;
   out_3778009894403191156[63] = 0.0;
   out_3778009894403191156[64] = 0.0;
   out_3778009894403191156[65] = 0.0;
   out_3778009894403191156[66] = 0.0;
   out_3778009894403191156[67] = 0.0;
   out_3778009894403191156[68] = 0.0;
   out_3778009894403191156[69] = 0.0;
   out_3778009894403191156[70] = 0.0;
   out_3778009894403191156[71] = 0.0;
   out_3778009894403191156[72] = 0.0;
   out_3778009894403191156[73] = 0.0;
   out_3778009894403191156[74] = 0.0;
   out_3778009894403191156[75] = 0.0;
   out_3778009894403191156[76] = 1.0;
   out_3778009894403191156[77] = 0.0;
   out_3778009894403191156[78] = 0.0;
   out_3778009894403191156[79] = 0.0;
   out_3778009894403191156[80] = 0.0;
   out_3778009894403191156[81] = 0.0;
   out_3778009894403191156[82] = 0.0;
   out_3778009894403191156[83] = 0.0;
   out_3778009894403191156[84] = 0.0;
   out_3778009894403191156[85] = 0.0;
   out_3778009894403191156[86] = 0.0;
   out_3778009894403191156[87] = 0.0;
   out_3778009894403191156[88] = 0.0;
   out_3778009894403191156[89] = 0.0;
   out_3778009894403191156[90] = 0.0;
   out_3778009894403191156[91] = 0.0;
   out_3778009894403191156[92] = 0.0;
   out_3778009894403191156[93] = 0.0;
   out_3778009894403191156[94] = 0.0;
   out_3778009894403191156[95] = 1.0;
   out_3778009894403191156[96] = 0.0;
   out_3778009894403191156[97] = 0.0;
   out_3778009894403191156[98] = 0.0;
   out_3778009894403191156[99] = 0.0;
   out_3778009894403191156[100] = 0.0;
   out_3778009894403191156[101] = 0.0;
   out_3778009894403191156[102] = 0.0;
   out_3778009894403191156[103] = 0.0;
   out_3778009894403191156[104] = 0.0;
   out_3778009894403191156[105] = 0.0;
   out_3778009894403191156[106] = 0.0;
   out_3778009894403191156[107] = 0.0;
   out_3778009894403191156[108] = 0.0;
   out_3778009894403191156[109] = 0.0;
   out_3778009894403191156[110] = 0.0;
   out_3778009894403191156[111] = 0.0;
   out_3778009894403191156[112] = 0.0;
   out_3778009894403191156[113] = 0.0;
   out_3778009894403191156[114] = 1.0;
   out_3778009894403191156[115] = 0.0;
   out_3778009894403191156[116] = 0.0;
   out_3778009894403191156[117] = 0.0;
   out_3778009894403191156[118] = 0.0;
   out_3778009894403191156[119] = 0.0;
   out_3778009894403191156[120] = 0.0;
   out_3778009894403191156[121] = 0.0;
   out_3778009894403191156[122] = 0.0;
   out_3778009894403191156[123] = 0.0;
   out_3778009894403191156[124] = 0.0;
   out_3778009894403191156[125] = 0.0;
   out_3778009894403191156[126] = 0.0;
   out_3778009894403191156[127] = 0.0;
   out_3778009894403191156[128] = 0.0;
   out_3778009894403191156[129] = 0.0;
   out_3778009894403191156[130] = 0.0;
   out_3778009894403191156[131] = 0.0;
   out_3778009894403191156[132] = 0.0;
   out_3778009894403191156[133] = 1.0;
   out_3778009894403191156[134] = 0.0;
   out_3778009894403191156[135] = 0.0;
   out_3778009894403191156[136] = 0.0;
   out_3778009894403191156[137] = 0.0;
   out_3778009894403191156[138] = 0.0;
   out_3778009894403191156[139] = 0.0;
   out_3778009894403191156[140] = 0.0;
   out_3778009894403191156[141] = 0.0;
   out_3778009894403191156[142] = 0.0;
   out_3778009894403191156[143] = 0.0;
   out_3778009894403191156[144] = 0.0;
   out_3778009894403191156[145] = 0.0;
   out_3778009894403191156[146] = 0.0;
   out_3778009894403191156[147] = 0.0;
   out_3778009894403191156[148] = 0.0;
   out_3778009894403191156[149] = 0.0;
   out_3778009894403191156[150] = 0.0;
   out_3778009894403191156[151] = 0.0;
   out_3778009894403191156[152] = 1.0;
   out_3778009894403191156[153] = 0.0;
   out_3778009894403191156[154] = 0.0;
   out_3778009894403191156[155] = 0.0;
   out_3778009894403191156[156] = 0.0;
   out_3778009894403191156[157] = 0.0;
   out_3778009894403191156[158] = 0.0;
   out_3778009894403191156[159] = 0.0;
   out_3778009894403191156[160] = 0.0;
   out_3778009894403191156[161] = 0.0;
   out_3778009894403191156[162] = 0.0;
   out_3778009894403191156[163] = 0.0;
   out_3778009894403191156[164] = 0.0;
   out_3778009894403191156[165] = 0.0;
   out_3778009894403191156[166] = 0.0;
   out_3778009894403191156[167] = 0.0;
   out_3778009894403191156[168] = 0.0;
   out_3778009894403191156[169] = 0.0;
   out_3778009894403191156[170] = 0.0;
   out_3778009894403191156[171] = 1.0;
   out_3778009894403191156[172] = 0.0;
   out_3778009894403191156[173] = 0.0;
   out_3778009894403191156[174] = 0.0;
   out_3778009894403191156[175] = 0.0;
   out_3778009894403191156[176] = 0.0;
   out_3778009894403191156[177] = 0.0;
   out_3778009894403191156[178] = 0.0;
   out_3778009894403191156[179] = 0.0;
   out_3778009894403191156[180] = 0.0;
   out_3778009894403191156[181] = 0.0;
   out_3778009894403191156[182] = 0.0;
   out_3778009894403191156[183] = 0.0;
   out_3778009894403191156[184] = 0.0;
   out_3778009894403191156[185] = 0.0;
   out_3778009894403191156[186] = 0.0;
   out_3778009894403191156[187] = 0.0;
   out_3778009894403191156[188] = 0.0;
   out_3778009894403191156[189] = 0.0;
   out_3778009894403191156[190] = 1.0;
   out_3778009894403191156[191] = 0.0;
   out_3778009894403191156[192] = 0.0;
   out_3778009894403191156[193] = 0.0;
   out_3778009894403191156[194] = 0.0;
   out_3778009894403191156[195] = 0.0;
   out_3778009894403191156[196] = 0.0;
   out_3778009894403191156[197] = 0.0;
   out_3778009894403191156[198] = 0.0;
   out_3778009894403191156[199] = 0.0;
   out_3778009894403191156[200] = 0.0;
   out_3778009894403191156[201] = 0.0;
   out_3778009894403191156[202] = 0.0;
   out_3778009894403191156[203] = 0.0;
   out_3778009894403191156[204] = 0.0;
   out_3778009894403191156[205] = 0.0;
   out_3778009894403191156[206] = 0.0;
   out_3778009894403191156[207] = 0.0;
   out_3778009894403191156[208] = 0.0;
   out_3778009894403191156[209] = 1.0;
   out_3778009894403191156[210] = 0.0;
   out_3778009894403191156[211] = 0.0;
   out_3778009894403191156[212] = 0.0;
   out_3778009894403191156[213] = 0.0;
   out_3778009894403191156[214] = 0.0;
   out_3778009894403191156[215] = 0.0;
   out_3778009894403191156[216] = 0.0;
   out_3778009894403191156[217] = 0.0;
   out_3778009894403191156[218] = 0.0;
   out_3778009894403191156[219] = 0.0;
   out_3778009894403191156[220] = 0.0;
   out_3778009894403191156[221] = 0.0;
   out_3778009894403191156[222] = 0.0;
   out_3778009894403191156[223] = 0.0;
   out_3778009894403191156[224] = 0.0;
   out_3778009894403191156[225] = 0.0;
   out_3778009894403191156[226] = 0.0;
   out_3778009894403191156[227] = 0.0;
   out_3778009894403191156[228] = 1.0;
   out_3778009894403191156[229] = 0.0;
   out_3778009894403191156[230] = 0.0;
   out_3778009894403191156[231] = 0.0;
   out_3778009894403191156[232] = 0.0;
   out_3778009894403191156[233] = 0.0;
   out_3778009894403191156[234] = 0.0;
   out_3778009894403191156[235] = 0.0;
   out_3778009894403191156[236] = 0.0;
   out_3778009894403191156[237] = 0.0;
   out_3778009894403191156[238] = 0.0;
   out_3778009894403191156[239] = 0.0;
   out_3778009894403191156[240] = 0.0;
   out_3778009894403191156[241] = 0.0;
   out_3778009894403191156[242] = 0.0;
   out_3778009894403191156[243] = 0.0;
   out_3778009894403191156[244] = 0.0;
   out_3778009894403191156[245] = 0.0;
   out_3778009894403191156[246] = 0.0;
   out_3778009894403191156[247] = 1.0;
   out_3778009894403191156[248] = 0.0;
   out_3778009894403191156[249] = 0.0;
   out_3778009894403191156[250] = 0.0;
   out_3778009894403191156[251] = 0.0;
   out_3778009894403191156[252] = 0.0;
   out_3778009894403191156[253] = 0.0;
   out_3778009894403191156[254] = 0.0;
   out_3778009894403191156[255] = 0.0;
   out_3778009894403191156[256] = 0.0;
   out_3778009894403191156[257] = 0.0;
   out_3778009894403191156[258] = 0.0;
   out_3778009894403191156[259] = 0.0;
   out_3778009894403191156[260] = 0.0;
   out_3778009894403191156[261] = 0.0;
   out_3778009894403191156[262] = 0.0;
   out_3778009894403191156[263] = 0.0;
   out_3778009894403191156[264] = 0.0;
   out_3778009894403191156[265] = 0.0;
   out_3778009894403191156[266] = 1.0;
   out_3778009894403191156[267] = 0.0;
   out_3778009894403191156[268] = 0.0;
   out_3778009894403191156[269] = 0.0;
   out_3778009894403191156[270] = 0.0;
   out_3778009894403191156[271] = 0.0;
   out_3778009894403191156[272] = 0.0;
   out_3778009894403191156[273] = 0.0;
   out_3778009894403191156[274] = 0.0;
   out_3778009894403191156[275] = 0.0;
   out_3778009894403191156[276] = 0.0;
   out_3778009894403191156[277] = 0.0;
   out_3778009894403191156[278] = 0.0;
   out_3778009894403191156[279] = 0.0;
   out_3778009894403191156[280] = 0.0;
   out_3778009894403191156[281] = 0.0;
   out_3778009894403191156[282] = 0.0;
   out_3778009894403191156[283] = 0.0;
   out_3778009894403191156[284] = 0.0;
   out_3778009894403191156[285] = 1.0;
   out_3778009894403191156[286] = 0.0;
   out_3778009894403191156[287] = 0.0;
   out_3778009894403191156[288] = 0.0;
   out_3778009894403191156[289] = 0.0;
   out_3778009894403191156[290] = 0.0;
   out_3778009894403191156[291] = 0.0;
   out_3778009894403191156[292] = 0.0;
   out_3778009894403191156[293] = 0.0;
   out_3778009894403191156[294] = 0.0;
   out_3778009894403191156[295] = 0.0;
   out_3778009894403191156[296] = 0.0;
   out_3778009894403191156[297] = 0.0;
   out_3778009894403191156[298] = 0.0;
   out_3778009894403191156[299] = 0.0;
   out_3778009894403191156[300] = 0.0;
   out_3778009894403191156[301] = 0.0;
   out_3778009894403191156[302] = 0.0;
   out_3778009894403191156[303] = 0.0;
   out_3778009894403191156[304] = 1.0;
   out_3778009894403191156[305] = 0.0;
   out_3778009894403191156[306] = 0.0;
   out_3778009894403191156[307] = 0.0;
   out_3778009894403191156[308] = 0.0;
   out_3778009894403191156[309] = 0.0;
   out_3778009894403191156[310] = 0.0;
   out_3778009894403191156[311] = 0.0;
   out_3778009894403191156[312] = 0.0;
   out_3778009894403191156[313] = 0.0;
   out_3778009894403191156[314] = 0.0;
   out_3778009894403191156[315] = 0.0;
   out_3778009894403191156[316] = 0.0;
   out_3778009894403191156[317] = 0.0;
   out_3778009894403191156[318] = 0.0;
   out_3778009894403191156[319] = 0.0;
   out_3778009894403191156[320] = 0.0;
   out_3778009894403191156[321] = 0.0;
   out_3778009894403191156[322] = 0.0;
   out_3778009894403191156[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8134339984135029222) {
   out_8134339984135029222[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8134339984135029222[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8134339984135029222[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8134339984135029222[3] = dt*state[12] + state[3];
   out_8134339984135029222[4] = dt*state[13] + state[4];
   out_8134339984135029222[5] = dt*state[14] + state[5];
   out_8134339984135029222[6] = state[6];
   out_8134339984135029222[7] = state[7];
   out_8134339984135029222[8] = state[8];
   out_8134339984135029222[9] = state[9];
   out_8134339984135029222[10] = state[10];
   out_8134339984135029222[11] = state[11];
   out_8134339984135029222[12] = state[12];
   out_8134339984135029222[13] = state[13];
   out_8134339984135029222[14] = state[14];
   out_8134339984135029222[15] = state[15];
   out_8134339984135029222[16] = state[16];
   out_8134339984135029222[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4223035310147805923) {
   out_4223035310147805923[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4223035310147805923[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4223035310147805923[2] = 0;
   out_4223035310147805923[3] = 0;
   out_4223035310147805923[4] = 0;
   out_4223035310147805923[5] = 0;
   out_4223035310147805923[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4223035310147805923[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4223035310147805923[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4223035310147805923[9] = 0;
   out_4223035310147805923[10] = 0;
   out_4223035310147805923[11] = 0;
   out_4223035310147805923[12] = 0;
   out_4223035310147805923[13] = 0;
   out_4223035310147805923[14] = 0;
   out_4223035310147805923[15] = 0;
   out_4223035310147805923[16] = 0;
   out_4223035310147805923[17] = 0;
   out_4223035310147805923[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4223035310147805923[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4223035310147805923[20] = 0;
   out_4223035310147805923[21] = 0;
   out_4223035310147805923[22] = 0;
   out_4223035310147805923[23] = 0;
   out_4223035310147805923[24] = 0;
   out_4223035310147805923[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4223035310147805923[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4223035310147805923[27] = 0;
   out_4223035310147805923[28] = 0;
   out_4223035310147805923[29] = 0;
   out_4223035310147805923[30] = 0;
   out_4223035310147805923[31] = 0;
   out_4223035310147805923[32] = 0;
   out_4223035310147805923[33] = 0;
   out_4223035310147805923[34] = 0;
   out_4223035310147805923[35] = 0;
   out_4223035310147805923[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4223035310147805923[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4223035310147805923[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4223035310147805923[39] = 0;
   out_4223035310147805923[40] = 0;
   out_4223035310147805923[41] = 0;
   out_4223035310147805923[42] = 0;
   out_4223035310147805923[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4223035310147805923[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4223035310147805923[45] = 0;
   out_4223035310147805923[46] = 0;
   out_4223035310147805923[47] = 0;
   out_4223035310147805923[48] = 0;
   out_4223035310147805923[49] = 0;
   out_4223035310147805923[50] = 0;
   out_4223035310147805923[51] = 0;
   out_4223035310147805923[52] = 0;
   out_4223035310147805923[53] = 0;
   out_4223035310147805923[54] = 0;
   out_4223035310147805923[55] = 0;
   out_4223035310147805923[56] = 0;
   out_4223035310147805923[57] = 1;
   out_4223035310147805923[58] = 0;
   out_4223035310147805923[59] = 0;
   out_4223035310147805923[60] = 0;
   out_4223035310147805923[61] = 0;
   out_4223035310147805923[62] = 0;
   out_4223035310147805923[63] = 0;
   out_4223035310147805923[64] = 0;
   out_4223035310147805923[65] = 0;
   out_4223035310147805923[66] = dt;
   out_4223035310147805923[67] = 0;
   out_4223035310147805923[68] = 0;
   out_4223035310147805923[69] = 0;
   out_4223035310147805923[70] = 0;
   out_4223035310147805923[71] = 0;
   out_4223035310147805923[72] = 0;
   out_4223035310147805923[73] = 0;
   out_4223035310147805923[74] = 0;
   out_4223035310147805923[75] = 0;
   out_4223035310147805923[76] = 1;
   out_4223035310147805923[77] = 0;
   out_4223035310147805923[78] = 0;
   out_4223035310147805923[79] = 0;
   out_4223035310147805923[80] = 0;
   out_4223035310147805923[81] = 0;
   out_4223035310147805923[82] = 0;
   out_4223035310147805923[83] = 0;
   out_4223035310147805923[84] = 0;
   out_4223035310147805923[85] = dt;
   out_4223035310147805923[86] = 0;
   out_4223035310147805923[87] = 0;
   out_4223035310147805923[88] = 0;
   out_4223035310147805923[89] = 0;
   out_4223035310147805923[90] = 0;
   out_4223035310147805923[91] = 0;
   out_4223035310147805923[92] = 0;
   out_4223035310147805923[93] = 0;
   out_4223035310147805923[94] = 0;
   out_4223035310147805923[95] = 1;
   out_4223035310147805923[96] = 0;
   out_4223035310147805923[97] = 0;
   out_4223035310147805923[98] = 0;
   out_4223035310147805923[99] = 0;
   out_4223035310147805923[100] = 0;
   out_4223035310147805923[101] = 0;
   out_4223035310147805923[102] = 0;
   out_4223035310147805923[103] = 0;
   out_4223035310147805923[104] = dt;
   out_4223035310147805923[105] = 0;
   out_4223035310147805923[106] = 0;
   out_4223035310147805923[107] = 0;
   out_4223035310147805923[108] = 0;
   out_4223035310147805923[109] = 0;
   out_4223035310147805923[110] = 0;
   out_4223035310147805923[111] = 0;
   out_4223035310147805923[112] = 0;
   out_4223035310147805923[113] = 0;
   out_4223035310147805923[114] = 1;
   out_4223035310147805923[115] = 0;
   out_4223035310147805923[116] = 0;
   out_4223035310147805923[117] = 0;
   out_4223035310147805923[118] = 0;
   out_4223035310147805923[119] = 0;
   out_4223035310147805923[120] = 0;
   out_4223035310147805923[121] = 0;
   out_4223035310147805923[122] = 0;
   out_4223035310147805923[123] = 0;
   out_4223035310147805923[124] = 0;
   out_4223035310147805923[125] = 0;
   out_4223035310147805923[126] = 0;
   out_4223035310147805923[127] = 0;
   out_4223035310147805923[128] = 0;
   out_4223035310147805923[129] = 0;
   out_4223035310147805923[130] = 0;
   out_4223035310147805923[131] = 0;
   out_4223035310147805923[132] = 0;
   out_4223035310147805923[133] = 1;
   out_4223035310147805923[134] = 0;
   out_4223035310147805923[135] = 0;
   out_4223035310147805923[136] = 0;
   out_4223035310147805923[137] = 0;
   out_4223035310147805923[138] = 0;
   out_4223035310147805923[139] = 0;
   out_4223035310147805923[140] = 0;
   out_4223035310147805923[141] = 0;
   out_4223035310147805923[142] = 0;
   out_4223035310147805923[143] = 0;
   out_4223035310147805923[144] = 0;
   out_4223035310147805923[145] = 0;
   out_4223035310147805923[146] = 0;
   out_4223035310147805923[147] = 0;
   out_4223035310147805923[148] = 0;
   out_4223035310147805923[149] = 0;
   out_4223035310147805923[150] = 0;
   out_4223035310147805923[151] = 0;
   out_4223035310147805923[152] = 1;
   out_4223035310147805923[153] = 0;
   out_4223035310147805923[154] = 0;
   out_4223035310147805923[155] = 0;
   out_4223035310147805923[156] = 0;
   out_4223035310147805923[157] = 0;
   out_4223035310147805923[158] = 0;
   out_4223035310147805923[159] = 0;
   out_4223035310147805923[160] = 0;
   out_4223035310147805923[161] = 0;
   out_4223035310147805923[162] = 0;
   out_4223035310147805923[163] = 0;
   out_4223035310147805923[164] = 0;
   out_4223035310147805923[165] = 0;
   out_4223035310147805923[166] = 0;
   out_4223035310147805923[167] = 0;
   out_4223035310147805923[168] = 0;
   out_4223035310147805923[169] = 0;
   out_4223035310147805923[170] = 0;
   out_4223035310147805923[171] = 1;
   out_4223035310147805923[172] = 0;
   out_4223035310147805923[173] = 0;
   out_4223035310147805923[174] = 0;
   out_4223035310147805923[175] = 0;
   out_4223035310147805923[176] = 0;
   out_4223035310147805923[177] = 0;
   out_4223035310147805923[178] = 0;
   out_4223035310147805923[179] = 0;
   out_4223035310147805923[180] = 0;
   out_4223035310147805923[181] = 0;
   out_4223035310147805923[182] = 0;
   out_4223035310147805923[183] = 0;
   out_4223035310147805923[184] = 0;
   out_4223035310147805923[185] = 0;
   out_4223035310147805923[186] = 0;
   out_4223035310147805923[187] = 0;
   out_4223035310147805923[188] = 0;
   out_4223035310147805923[189] = 0;
   out_4223035310147805923[190] = 1;
   out_4223035310147805923[191] = 0;
   out_4223035310147805923[192] = 0;
   out_4223035310147805923[193] = 0;
   out_4223035310147805923[194] = 0;
   out_4223035310147805923[195] = 0;
   out_4223035310147805923[196] = 0;
   out_4223035310147805923[197] = 0;
   out_4223035310147805923[198] = 0;
   out_4223035310147805923[199] = 0;
   out_4223035310147805923[200] = 0;
   out_4223035310147805923[201] = 0;
   out_4223035310147805923[202] = 0;
   out_4223035310147805923[203] = 0;
   out_4223035310147805923[204] = 0;
   out_4223035310147805923[205] = 0;
   out_4223035310147805923[206] = 0;
   out_4223035310147805923[207] = 0;
   out_4223035310147805923[208] = 0;
   out_4223035310147805923[209] = 1;
   out_4223035310147805923[210] = 0;
   out_4223035310147805923[211] = 0;
   out_4223035310147805923[212] = 0;
   out_4223035310147805923[213] = 0;
   out_4223035310147805923[214] = 0;
   out_4223035310147805923[215] = 0;
   out_4223035310147805923[216] = 0;
   out_4223035310147805923[217] = 0;
   out_4223035310147805923[218] = 0;
   out_4223035310147805923[219] = 0;
   out_4223035310147805923[220] = 0;
   out_4223035310147805923[221] = 0;
   out_4223035310147805923[222] = 0;
   out_4223035310147805923[223] = 0;
   out_4223035310147805923[224] = 0;
   out_4223035310147805923[225] = 0;
   out_4223035310147805923[226] = 0;
   out_4223035310147805923[227] = 0;
   out_4223035310147805923[228] = 1;
   out_4223035310147805923[229] = 0;
   out_4223035310147805923[230] = 0;
   out_4223035310147805923[231] = 0;
   out_4223035310147805923[232] = 0;
   out_4223035310147805923[233] = 0;
   out_4223035310147805923[234] = 0;
   out_4223035310147805923[235] = 0;
   out_4223035310147805923[236] = 0;
   out_4223035310147805923[237] = 0;
   out_4223035310147805923[238] = 0;
   out_4223035310147805923[239] = 0;
   out_4223035310147805923[240] = 0;
   out_4223035310147805923[241] = 0;
   out_4223035310147805923[242] = 0;
   out_4223035310147805923[243] = 0;
   out_4223035310147805923[244] = 0;
   out_4223035310147805923[245] = 0;
   out_4223035310147805923[246] = 0;
   out_4223035310147805923[247] = 1;
   out_4223035310147805923[248] = 0;
   out_4223035310147805923[249] = 0;
   out_4223035310147805923[250] = 0;
   out_4223035310147805923[251] = 0;
   out_4223035310147805923[252] = 0;
   out_4223035310147805923[253] = 0;
   out_4223035310147805923[254] = 0;
   out_4223035310147805923[255] = 0;
   out_4223035310147805923[256] = 0;
   out_4223035310147805923[257] = 0;
   out_4223035310147805923[258] = 0;
   out_4223035310147805923[259] = 0;
   out_4223035310147805923[260] = 0;
   out_4223035310147805923[261] = 0;
   out_4223035310147805923[262] = 0;
   out_4223035310147805923[263] = 0;
   out_4223035310147805923[264] = 0;
   out_4223035310147805923[265] = 0;
   out_4223035310147805923[266] = 1;
   out_4223035310147805923[267] = 0;
   out_4223035310147805923[268] = 0;
   out_4223035310147805923[269] = 0;
   out_4223035310147805923[270] = 0;
   out_4223035310147805923[271] = 0;
   out_4223035310147805923[272] = 0;
   out_4223035310147805923[273] = 0;
   out_4223035310147805923[274] = 0;
   out_4223035310147805923[275] = 0;
   out_4223035310147805923[276] = 0;
   out_4223035310147805923[277] = 0;
   out_4223035310147805923[278] = 0;
   out_4223035310147805923[279] = 0;
   out_4223035310147805923[280] = 0;
   out_4223035310147805923[281] = 0;
   out_4223035310147805923[282] = 0;
   out_4223035310147805923[283] = 0;
   out_4223035310147805923[284] = 0;
   out_4223035310147805923[285] = 1;
   out_4223035310147805923[286] = 0;
   out_4223035310147805923[287] = 0;
   out_4223035310147805923[288] = 0;
   out_4223035310147805923[289] = 0;
   out_4223035310147805923[290] = 0;
   out_4223035310147805923[291] = 0;
   out_4223035310147805923[292] = 0;
   out_4223035310147805923[293] = 0;
   out_4223035310147805923[294] = 0;
   out_4223035310147805923[295] = 0;
   out_4223035310147805923[296] = 0;
   out_4223035310147805923[297] = 0;
   out_4223035310147805923[298] = 0;
   out_4223035310147805923[299] = 0;
   out_4223035310147805923[300] = 0;
   out_4223035310147805923[301] = 0;
   out_4223035310147805923[302] = 0;
   out_4223035310147805923[303] = 0;
   out_4223035310147805923[304] = 1;
   out_4223035310147805923[305] = 0;
   out_4223035310147805923[306] = 0;
   out_4223035310147805923[307] = 0;
   out_4223035310147805923[308] = 0;
   out_4223035310147805923[309] = 0;
   out_4223035310147805923[310] = 0;
   out_4223035310147805923[311] = 0;
   out_4223035310147805923[312] = 0;
   out_4223035310147805923[313] = 0;
   out_4223035310147805923[314] = 0;
   out_4223035310147805923[315] = 0;
   out_4223035310147805923[316] = 0;
   out_4223035310147805923[317] = 0;
   out_4223035310147805923[318] = 0;
   out_4223035310147805923[319] = 0;
   out_4223035310147805923[320] = 0;
   out_4223035310147805923[321] = 0;
   out_4223035310147805923[322] = 0;
   out_4223035310147805923[323] = 1;
}
void h_4(double *state, double *unused, double *out_3703400346234585599) {
   out_3703400346234585599[0] = state[6] + state[9];
   out_3703400346234585599[1] = state[7] + state[10];
   out_3703400346234585599[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7549817104247098728) {
   out_7549817104247098728[0] = 0;
   out_7549817104247098728[1] = 0;
   out_7549817104247098728[2] = 0;
   out_7549817104247098728[3] = 0;
   out_7549817104247098728[4] = 0;
   out_7549817104247098728[5] = 0;
   out_7549817104247098728[6] = 1;
   out_7549817104247098728[7] = 0;
   out_7549817104247098728[8] = 0;
   out_7549817104247098728[9] = 1;
   out_7549817104247098728[10] = 0;
   out_7549817104247098728[11] = 0;
   out_7549817104247098728[12] = 0;
   out_7549817104247098728[13] = 0;
   out_7549817104247098728[14] = 0;
   out_7549817104247098728[15] = 0;
   out_7549817104247098728[16] = 0;
   out_7549817104247098728[17] = 0;
   out_7549817104247098728[18] = 0;
   out_7549817104247098728[19] = 0;
   out_7549817104247098728[20] = 0;
   out_7549817104247098728[21] = 0;
   out_7549817104247098728[22] = 0;
   out_7549817104247098728[23] = 0;
   out_7549817104247098728[24] = 0;
   out_7549817104247098728[25] = 1;
   out_7549817104247098728[26] = 0;
   out_7549817104247098728[27] = 0;
   out_7549817104247098728[28] = 1;
   out_7549817104247098728[29] = 0;
   out_7549817104247098728[30] = 0;
   out_7549817104247098728[31] = 0;
   out_7549817104247098728[32] = 0;
   out_7549817104247098728[33] = 0;
   out_7549817104247098728[34] = 0;
   out_7549817104247098728[35] = 0;
   out_7549817104247098728[36] = 0;
   out_7549817104247098728[37] = 0;
   out_7549817104247098728[38] = 0;
   out_7549817104247098728[39] = 0;
   out_7549817104247098728[40] = 0;
   out_7549817104247098728[41] = 0;
   out_7549817104247098728[42] = 0;
   out_7549817104247098728[43] = 0;
   out_7549817104247098728[44] = 1;
   out_7549817104247098728[45] = 0;
   out_7549817104247098728[46] = 0;
   out_7549817104247098728[47] = 1;
   out_7549817104247098728[48] = 0;
   out_7549817104247098728[49] = 0;
   out_7549817104247098728[50] = 0;
   out_7549817104247098728[51] = 0;
   out_7549817104247098728[52] = 0;
   out_7549817104247098728[53] = 0;
}
void h_10(double *state, double *unused, double *out_1721115505953865677) {
   out_1721115505953865677[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1721115505953865677[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1721115505953865677[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8217499614069688590) {
   out_8217499614069688590[0] = 0;
   out_8217499614069688590[1] = 9.8100000000000005*cos(state[1]);
   out_8217499614069688590[2] = 0;
   out_8217499614069688590[3] = 0;
   out_8217499614069688590[4] = -state[8];
   out_8217499614069688590[5] = state[7];
   out_8217499614069688590[6] = 0;
   out_8217499614069688590[7] = state[5];
   out_8217499614069688590[8] = -state[4];
   out_8217499614069688590[9] = 0;
   out_8217499614069688590[10] = 0;
   out_8217499614069688590[11] = 0;
   out_8217499614069688590[12] = 1;
   out_8217499614069688590[13] = 0;
   out_8217499614069688590[14] = 0;
   out_8217499614069688590[15] = 1;
   out_8217499614069688590[16] = 0;
   out_8217499614069688590[17] = 0;
   out_8217499614069688590[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8217499614069688590[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8217499614069688590[20] = 0;
   out_8217499614069688590[21] = state[8];
   out_8217499614069688590[22] = 0;
   out_8217499614069688590[23] = -state[6];
   out_8217499614069688590[24] = -state[5];
   out_8217499614069688590[25] = 0;
   out_8217499614069688590[26] = state[3];
   out_8217499614069688590[27] = 0;
   out_8217499614069688590[28] = 0;
   out_8217499614069688590[29] = 0;
   out_8217499614069688590[30] = 0;
   out_8217499614069688590[31] = 1;
   out_8217499614069688590[32] = 0;
   out_8217499614069688590[33] = 0;
   out_8217499614069688590[34] = 1;
   out_8217499614069688590[35] = 0;
   out_8217499614069688590[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8217499614069688590[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8217499614069688590[38] = 0;
   out_8217499614069688590[39] = -state[7];
   out_8217499614069688590[40] = state[6];
   out_8217499614069688590[41] = 0;
   out_8217499614069688590[42] = state[4];
   out_8217499614069688590[43] = -state[3];
   out_8217499614069688590[44] = 0;
   out_8217499614069688590[45] = 0;
   out_8217499614069688590[46] = 0;
   out_8217499614069688590[47] = 0;
   out_8217499614069688590[48] = 0;
   out_8217499614069688590[49] = 0;
   out_8217499614069688590[50] = 1;
   out_8217499614069688590[51] = 0;
   out_8217499614069688590[52] = 0;
   out_8217499614069688590[53] = 1;
}
void h_13(double *state, double *unused, double *out_4057181902355091495) {
   out_4057181902355091495[0] = state[3];
   out_4057181902355091495[1] = state[4];
   out_4057181902355091495[2] = state[5];
}
void H_13(double *state, double *unused, double *out_7684653144130120087) {
   out_7684653144130120087[0] = 0;
   out_7684653144130120087[1] = 0;
   out_7684653144130120087[2] = 0;
   out_7684653144130120087[3] = 1;
   out_7684653144130120087[4] = 0;
   out_7684653144130120087[5] = 0;
   out_7684653144130120087[6] = 0;
   out_7684653144130120087[7] = 0;
   out_7684653144130120087[8] = 0;
   out_7684653144130120087[9] = 0;
   out_7684653144130120087[10] = 0;
   out_7684653144130120087[11] = 0;
   out_7684653144130120087[12] = 0;
   out_7684653144130120087[13] = 0;
   out_7684653144130120087[14] = 0;
   out_7684653144130120087[15] = 0;
   out_7684653144130120087[16] = 0;
   out_7684653144130120087[17] = 0;
   out_7684653144130120087[18] = 0;
   out_7684653144130120087[19] = 0;
   out_7684653144130120087[20] = 0;
   out_7684653144130120087[21] = 0;
   out_7684653144130120087[22] = 1;
   out_7684653144130120087[23] = 0;
   out_7684653144130120087[24] = 0;
   out_7684653144130120087[25] = 0;
   out_7684653144130120087[26] = 0;
   out_7684653144130120087[27] = 0;
   out_7684653144130120087[28] = 0;
   out_7684653144130120087[29] = 0;
   out_7684653144130120087[30] = 0;
   out_7684653144130120087[31] = 0;
   out_7684653144130120087[32] = 0;
   out_7684653144130120087[33] = 0;
   out_7684653144130120087[34] = 0;
   out_7684653144130120087[35] = 0;
   out_7684653144130120087[36] = 0;
   out_7684653144130120087[37] = 0;
   out_7684653144130120087[38] = 0;
   out_7684653144130120087[39] = 0;
   out_7684653144130120087[40] = 0;
   out_7684653144130120087[41] = 1;
   out_7684653144130120087[42] = 0;
   out_7684653144130120087[43] = 0;
   out_7684653144130120087[44] = 0;
   out_7684653144130120087[45] = 0;
   out_7684653144130120087[46] = 0;
   out_7684653144130120087[47] = 0;
   out_7684653144130120087[48] = 0;
   out_7684653144130120087[49] = 0;
   out_7684653144130120087[50] = 0;
   out_7684653144130120087[51] = 0;
   out_7684653144130120087[52] = 0;
   out_7684653144130120087[53] = 0;
}
void h_14(double *state, double *unused, double *out_3026553806307433649) {
   out_3026553806307433649[0] = state[6];
   out_3026553806307433649[1] = state[7];
   out_3026553806307433649[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4467028671951726432) {
   out_4467028671951726432[0] = 0;
   out_4467028671951726432[1] = 0;
   out_4467028671951726432[2] = 0;
   out_4467028671951726432[3] = 0;
   out_4467028671951726432[4] = 0;
   out_4467028671951726432[5] = 0;
   out_4467028671951726432[6] = 1;
   out_4467028671951726432[7] = 0;
   out_4467028671951726432[8] = 0;
   out_4467028671951726432[9] = 0;
   out_4467028671951726432[10] = 0;
   out_4467028671951726432[11] = 0;
   out_4467028671951726432[12] = 0;
   out_4467028671951726432[13] = 0;
   out_4467028671951726432[14] = 0;
   out_4467028671951726432[15] = 0;
   out_4467028671951726432[16] = 0;
   out_4467028671951726432[17] = 0;
   out_4467028671951726432[18] = 0;
   out_4467028671951726432[19] = 0;
   out_4467028671951726432[20] = 0;
   out_4467028671951726432[21] = 0;
   out_4467028671951726432[22] = 0;
   out_4467028671951726432[23] = 0;
   out_4467028671951726432[24] = 0;
   out_4467028671951726432[25] = 1;
   out_4467028671951726432[26] = 0;
   out_4467028671951726432[27] = 0;
   out_4467028671951726432[28] = 0;
   out_4467028671951726432[29] = 0;
   out_4467028671951726432[30] = 0;
   out_4467028671951726432[31] = 0;
   out_4467028671951726432[32] = 0;
   out_4467028671951726432[33] = 0;
   out_4467028671951726432[34] = 0;
   out_4467028671951726432[35] = 0;
   out_4467028671951726432[36] = 0;
   out_4467028671951726432[37] = 0;
   out_4467028671951726432[38] = 0;
   out_4467028671951726432[39] = 0;
   out_4467028671951726432[40] = 0;
   out_4467028671951726432[41] = 0;
   out_4467028671951726432[42] = 0;
   out_4467028671951726432[43] = 0;
   out_4467028671951726432[44] = 1;
   out_4467028671951726432[45] = 0;
   out_4467028671951726432[46] = 0;
   out_4467028671951726432[47] = 0;
   out_4467028671951726432[48] = 0;
   out_4467028671951726432[49] = 0;
   out_4467028671951726432[50] = 0;
   out_4467028671951726432[51] = 0;
   out_4467028671951726432[52] = 0;
   out_4467028671951726432[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_1686705028277529867) {
  err_fun(nom_x, delta_x, out_1686705028277529867);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1103979266905204510) {
  inv_err_fun(nom_x, true_x, out_1103979266905204510);
}
void pose_H_mod_fun(double *state, double *out_3778009894403191156) {
  H_mod_fun(state, out_3778009894403191156);
}
void pose_f_fun(double *state, double dt, double *out_8134339984135029222) {
  f_fun(state,  dt, out_8134339984135029222);
}
void pose_F_fun(double *state, double dt, double *out_4223035310147805923) {
  F_fun(state,  dt, out_4223035310147805923);
}
void pose_h_4(double *state, double *unused, double *out_3703400346234585599) {
  h_4(state, unused, out_3703400346234585599);
}
void pose_H_4(double *state, double *unused, double *out_7549817104247098728) {
  H_4(state, unused, out_7549817104247098728);
}
void pose_h_10(double *state, double *unused, double *out_1721115505953865677) {
  h_10(state, unused, out_1721115505953865677);
}
void pose_H_10(double *state, double *unused, double *out_8217499614069688590) {
  H_10(state, unused, out_8217499614069688590);
}
void pose_h_13(double *state, double *unused, double *out_4057181902355091495) {
  h_13(state, unused, out_4057181902355091495);
}
void pose_H_13(double *state, double *unused, double *out_7684653144130120087) {
  H_13(state, unused, out_7684653144130120087);
}
void pose_h_14(double *state, double *unused, double *out_3026553806307433649) {
  h_14(state, unused, out_3026553806307433649);
}
void pose_H_14(double *state, double *unused, double *out_4467028671951726432) {
  H_14(state, unused, out_4467028671951726432);
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
