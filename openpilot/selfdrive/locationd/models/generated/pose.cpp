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
void err_fun(double *nom_x, double *delta_x, double *out_4574623741916747896) {
   out_4574623741916747896[0] = delta_x[0] + nom_x[0];
   out_4574623741916747896[1] = delta_x[1] + nom_x[1];
   out_4574623741916747896[2] = delta_x[2] + nom_x[2];
   out_4574623741916747896[3] = delta_x[3] + nom_x[3];
   out_4574623741916747896[4] = delta_x[4] + nom_x[4];
   out_4574623741916747896[5] = delta_x[5] + nom_x[5];
   out_4574623741916747896[6] = delta_x[6] + nom_x[6];
   out_4574623741916747896[7] = delta_x[7] + nom_x[7];
   out_4574623741916747896[8] = delta_x[8] + nom_x[8];
   out_4574623741916747896[9] = delta_x[9] + nom_x[9];
   out_4574623741916747896[10] = delta_x[10] + nom_x[10];
   out_4574623741916747896[11] = delta_x[11] + nom_x[11];
   out_4574623741916747896[12] = delta_x[12] + nom_x[12];
   out_4574623741916747896[13] = delta_x[13] + nom_x[13];
   out_4574623741916747896[14] = delta_x[14] + nom_x[14];
   out_4574623741916747896[15] = delta_x[15] + nom_x[15];
   out_4574623741916747896[16] = delta_x[16] + nom_x[16];
   out_4574623741916747896[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2341160614075288752) {
   out_2341160614075288752[0] = -nom_x[0] + true_x[0];
   out_2341160614075288752[1] = -nom_x[1] + true_x[1];
   out_2341160614075288752[2] = -nom_x[2] + true_x[2];
   out_2341160614075288752[3] = -nom_x[3] + true_x[3];
   out_2341160614075288752[4] = -nom_x[4] + true_x[4];
   out_2341160614075288752[5] = -nom_x[5] + true_x[5];
   out_2341160614075288752[6] = -nom_x[6] + true_x[6];
   out_2341160614075288752[7] = -nom_x[7] + true_x[7];
   out_2341160614075288752[8] = -nom_x[8] + true_x[8];
   out_2341160614075288752[9] = -nom_x[9] + true_x[9];
   out_2341160614075288752[10] = -nom_x[10] + true_x[10];
   out_2341160614075288752[11] = -nom_x[11] + true_x[11];
   out_2341160614075288752[12] = -nom_x[12] + true_x[12];
   out_2341160614075288752[13] = -nom_x[13] + true_x[13];
   out_2341160614075288752[14] = -nom_x[14] + true_x[14];
   out_2341160614075288752[15] = -nom_x[15] + true_x[15];
   out_2341160614075288752[16] = -nom_x[16] + true_x[16];
   out_2341160614075288752[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8733031835894533596) {
   out_8733031835894533596[0] = 1.0;
   out_8733031835894533596[1] = 0.0;
   out_8733031835894533596[2] = 0.0;
   out_8733031835894533596[3] = 0.0;
   out_8733031835894533596[4] = 0.0;
   out_8733031835894533596[5] = 0.0;
   out_8733031835894533596[6] = 0.0;
   out_8733031835894533596[7] = 0.0;
   out_8733031835894533596[8] = 0.0;
   out_8733031835894533596[9] = 0.0;
   out_8733031835894533596[10] = 0.0;
   out_8733031835894533596[11] = 0.0;
   out_8733031835894533596[12] = 0.0;
   out_8733031835894533596[13] = 0.0;
   out_8733031835894533596[14] = 0.0;
   out_8733031835894533596[15] = 0.0;
   out_8733031835894533596[16] = 0.0;
   out_8733031835894533596[17] = 0.0;
   out_8733031835894533596[18] = 0.0;
   out_8733031835894533596[19] = 1.0;
   out_8733031835894533596[20] = 0.0;
   out_8733031835894533596[21] = 0.0;
   out_8733031835894533596[22] = 0.0;
   out_8733031835894533596[23] = 0.0;
   out_8733031835894533596[24] = 0.0;
   out_8733031835894533596[25] = 0.0;
   out_8733031835894533596[26] = 0.0;
   out_8733031835894533596[27] = 0.0;
   out_8733031835894533596[28] = 0.0;
   out_8733031835894533596[29] = 0.0;
   out_8733031835894533596[30] = 0.0;
   out_8733031835894533596[31] = 0.0;
   out_8733031835894533596[32] = 0.0;
   out_8733031835894533596[33] = 0.0;
   out_8733031835894533596[34] = 0.0;
   out_8733031835894533596[35] = 0.0;
   out_8733031835894533596[36] = 0.0;
   out_8733031835894533596[37] = 0.0;
   out_8733031835894533596[38] = 1.0;
   out_8733031835894533596[39] = 0.0;
   out_8733031835894533596[40] = 0.0;
   out_8733031835894533596[41] = 0.0;
   out_8733031835894533596[42] = 0.0;
   out_8733031835894533596[43] = 0.0;
   out_8733031835894533596[44] = 0.0;
   out_8733031835894533596[45] = 0.0;
   out_8733031835894533596[46] = 0.0;
   out_8733031835894533596[47] = 0.0;
   out_8733031835894533596[48] = 0.0;
   out_8733031835894533596[49] = 0.0;
   out_8733031835894533596[50] = 0.0;
   out_8733031835894533596[51] = 0.0;
   out_8733031835894533596[52] = 0.0;
   out_8733031835894533596[53] = 0.0;
   out_8733031835894533596[54] = 0.0;
   out_8733031835894533596[55] = 0.0;
   out_8733031835894533596[56] = 0.0;
   out_8733031835894533596[57] = 1.0;
   out_8733031835894533596[58] = 0.0;
   out_8733031835894533596[59] = 0.0;
   out_8733031835894533596[60] = 0.0;
   out_8733031835894533596[61] = 0.0;
   out_8733031835894533596[62] = 0.0;
   out_8733031835894533596[63] = 0.0;
   out_8733031835894533596[64] = 0.0;
   out_8733031835894533596[65] = 0.0;
   out_8733031835894533596[66] = 0.0;
   out_8733031835894533596[67] = 0.0;
   out_8733031835894533596[68] = 0.0;
   out_8733031835894533596[69] = 0.0;
   out_8733031835894533596[70] = 0.0;
   out_8733031835894533596[71] = 0.0;
   out_8733031835894533596[72] = 0.0;
   out_8733031835894533596[73] = 0.0;
   out_8733031835894533596[74] = 0.0;
   out_8733031835894533596[75] = 0.0;
   out_8733031835894533596[76] = 1.0;
   out_8733031835894533596[77] = 0.0;
   out_8733031835894533596[78] = 0.0;
   out_8733031835894533596[79] = 0.0;
   out_8733031835894533596[80] = 0.0;
   out_8733031835894533596[81] = 0.0;
   out_8733031835894533596[82] = 0.0;
   out_8733031835894533596[83] = 0.0;
   out_8733031835894533596[84] = 0.0;
   out_8733031835894533596[85] = 0.0;
   out_8733031835894533596[86] = 0.0;
   out_8733031835894533596[87] = 0.0;
   out_8733031835894533596[88] = 0.0;
   out_8733031835894533596[89] = 0.0;
   out_8733031835894533596[90] = 0.0;
   out_8733031835894533596[91] = 0.0;
   out_8733031835894533596[92] = 0.0;
   out_8733031835894533596[93] = 0.0;
   out_8733031835894533596[94] = 0.0;
   out_8733031835894533596[95] = 1.0;
   out_8733031835894533596[96] = 0.0;
   out_8733031835894533596[97] = 0.0;
   out_8733031835894533596[98] = 0.0;
   out_8733031835894533596[99] = 0.0;
   out_8733031835894533596[100] = 0.0;
   out_8733031835894533596[101] = 0.0;
   out_8733031835894533596[102] = 0.0;
   out_8733031835894533596[103] = 0.0;
   out_8733031835894533596[104] = 0.0;
   out_8733031835894533596[105] = 0.0;
   out_8733031835894533596[106] = 0.0;
   out_8733031835894533596[107] = 0.0;
   out_8733031835894533596[108] = 0.0;
   out_8733031835894533596[109] = 0.0;
   out_8733031835894533596[110] = 0.0;
   out_8733031835894533596[111] = 0.0;
   out_8733031835894533596[112] = 0.0;
   out_8733031835894533596[113] = 0.0;
   out_8733031835894533596[114] = 1.0;
   out_8733031835894533596[115] = 0.0;
   out_8733031835894533596[116] = 0.0;
   out_8733031835894533596[117] = 0.0;
   out_8733031835894533596[118] = 0.0;
   out_8733031835894533596[119] = 0.0;
   out_8733031835894533596[120] = 0.0;
   out_8733031835894533596[121] = 0.0;
   out_8733031835894533596[122] = 0.0;
   out_8733031835894533596[123] = 0.0;
   out_8733031835894533596[124] = 0.0;
   out_8733031835894533596[125] = 0.0;
   out_8733031835894533596[126] = 0.0;
   out_8733031835894533596[127] = 0.0;
   out_8733031835894533596[128] = 0.0;
   out_8733031835894533596[129] = 0.0;
   out_8733031835894533596[130] = 0.0;
   out_8733031835894533596[131] = 0.0;
   out_8733031835894533596[132] = 0.0;
   out_8733031835894533596[133] = 1.0;
   out_8733031835894533596[134] = 0.0;
   out_8733031835894533596[135] = 0.0;
   out_8733031835894533596[136] = 0.0;
   out_8733031835894533596[137] = 0.0;
   out_8733031835894533596[138] = 0.0;
   out_8733031835894533596[139] = 0.0;
   out_8733031835894533596[140] = 0.0;
   out_8733031835894533596[141] = 0.0;
   out_8733031835894533596[142] = 0.0;
   out_8733031835894533596[143] = 0.0;
   out_8733031835894533596[144] = 0.0;
   out_8733031835894533596[145] = 0.0;
   out_8733031835894533596[146] = 0.0;
   out_8733031835894533596[147] = 0.0;
   out_8733031835894533596[148] = 0.0;
   out_8733031835894533596[149] = 0.0;
   out_8733031835894533596[150] = 0.0;
   out_8733031835894533596[151] = 0.0;
   out_8733031835894533596[152] = 1.0;
   out_8733031835894533596[153] = 0.0;
   out_8733031835894533596[154] = 0.0;
   out_8733031835894533596[155] = 0.0;
   out_8733031835894533596[156] = 0.0;
   out_8733031835894533596[157] = 0.0;
   out_8733031835894533596[158] = 0.0;
   out_8733031835894533596[159] = 0.0;
   out_8733031835894533596[160] = 0.0;
   out_8733031835894533596[161] = 0.0;
   out_8733031835894533596[162] = 0.0;
   out_8733031835894533596[163] = 0.0;
   out_8733031835894533596[164] = 0.0;
   out_8733031835894533596[165] = 0.0;
   out_8733031835894533596[166] = 0.0;
   out_8733031835894533596[167] = 0.0;
   out_8733031835894533596[168] = 0.0;
   out_8733031835894533596[169] = 0.0;
   out_8733031835894533596[170] = 0.0;
   out_8733031835894533596[171] = 1.0;
   out_8733031835894533596[172] = 0.0;
   out_8733031835894533596[173] = 0.0;
   out_8733031835894533596[174] = 0.0;
   out_8733031835894533596[175] = 0.0;
   out_8733031835894533596[176] = 0.0;
   out_8733031835894533596[177] = 0.0;
   out_8733031835894533596[178] = 0.0;
   out_8733031835894533596[179] = 0.0;
   out_8733031835894533596[180] = 0.0;
   out_8733031835894533596[181] = 0.0;
   out_8733031835894533596[182] = 0.0;
   out_8733031835894533596[183] = 0.0;
   out_8733031835894533596[184] = 0.0;
   out_8733031835894533596[185] = 0.0;
   out_8733031835894533596[186] = 0.0;
   out_8733031835894533596[187] = 0.0;
   out_8733031835894533596[188] = 0.0;
   out_8733031835894533596[189] = 0.0;
   out_8733031835894533596[190] = 1.0;
   out_8733031835894533596[191] = 0.0;
   out_8733031835894533596[192] = 0.0;
   out_8733031835894533596[193] = 0.0;
   out_8733031835894533596[194] = 0.0;
   out_8733031835894533596[195] = 0.0;
   out_8733031835894533596[196] = 0.0;
   out_8733031835894533596[197] = 0.0;
   out_8733031835894533596[198] = 0.0;
   out_8733031835894533596[199] = 0.0;
   out_8733031835894533596[200] = 0.0;
   out_8733031835894533596[201] = 0.0;
   out_8733031835894533596[202] = 0.0;
   out_8733031835894533596[203] = 0.0;
   out_8733031835894533596[204] = 0.0;
   out_8733031835894533596[205] = 0.0;
   out_8733031835894533596[206] = 0.0;
   out_8733031835894533596[207] = 0.0;
   out_8733031835894533596[208] = 0.0;
   out_8733031835894533596[209] = 1.0;
   out_8733031835894533596[210] = 0.0;
   out_8733031835894533596[211] = 0.0;
   out_8733031835894533596[212] = 0.0;
   out_8733031835894533596[213] = 0.0;
   out_8733031835894533596[214] = 0.0;
   out_8733031835894533596[215] = 0.0;
   out_8733031835894533596[216] = 0.0;
   out_8733031835894533596[217] = 0.0;
   out_8733031835894533596[218] = 0.0;
   out_8733031835894533596[219] = 0.0;
   out_8733031835894533596[220] = 0.0;
   out_8733031835894533596[221] = 0.0;
   out_8733031835894533596[222] = 0.0;
   out_8733031835894533596[223] = 0.0;
   out_8733031835894533596[224] = 0.0;
   out_8733031835894533596[225] = 0.0;
   out_8733031835894533596[226] = 0.0;
   out_8733031835894533596[227] = 0.0;
   out_8733031835894533596[228] = 1.0;
   out_8733031835894533596[229] = 0.0;
   out_8733031835894533596[230] = 0.0;
   out_8733031835894533596[231] = 0.0;
   out_8733031835894533596[232] = 0.0;
   out_8733031835894533596[233] = 0.0;
   out_8733031835894533596[234] = 0.0;
   out_8733031835894533596[235] = 0.0;
   out_8733031835894533596[236] = 0.0;
   out_8733031835894533596[237] = 0.0;
   out_8733031835894533596[238] = 0.0;
   out_8733031835894533596[239] = 0.0;
   out_8733031835894533596[240] = 0.0;
   out_8733031835894533596[241] = 0.0;
   out_8733031835894533596[242] = 0.0;
   out_8733031835894533596[243] = 0.0;
   out_8733031835894533596[244] = 0.0;
   out_8733031835894533596[245] = 0.0;
   out_8733031835894533596[246] = 0.0;
   out_8733031835894533596[247] = 1.0;
   out_8733031835894533596[248] = 0.0;
   out_8733031835894533596[249] = 0.0;
   out_8733031835894533596[250] = 0.0;
   out_8733031835894533596[251] = 0.0;
   out_8733031835894533596[252] = 0.0;
   out_8733031835894533596[253] = 0.0;
   out_8733031835894533596[254] = 0.0;
   out_8733031835894533596[255] = 0.0;
   out_8733031835894533596[256] = 0.0;
   out_8733031835894533596[257] = 0.0;
   out_8733031835894533596[258] = 0.0;
   out_8733031835894533596[259] = 0.0;
   out_8733031835894533596[260] = 0.0;
   out_8733031835894533596[261] = 0.0;
   out_8733031835894533596[262] = 0.0;
   out_8733031835894533596[263] = 0.0;
   out_8733031835894533596[264] = 0.0;
   out_8733031835894533596[265] = 0.0;
   out_8733031835894533596[266] = 1.0;
   out_8733031835894533596[267] = 0.0;
   out_8733031835894533596[268] = 0.0;
   out_8733031835894533596[269] = 0.0;
   out_8733031835894533596[270] = 0.0;
   out_8733031835894533596[271] = 0.0;
   out_8733031835894533596[272] = 0.0;
   out_8733031835894533596[273] = 0.0;
   out_8733031835894533596[274] = 0.0;
   out_8733031835894533596[275] = 0.0;
   out_8733031835894533596[276] = 0.0;
   out_8733031835894533596[277] = 0.0;
   out_8733031835894533596[278] = 0.0;
   out_8733031835894533596[279] = 0.0;
   out_8733031835894533596[280] = 0.0;
   out_8733031835894533596[281] = 0.0;
   out_8733031835894533596[282] = 0.0;
   out_8733031835894533596[283] = 0.0;
   out_8733031835894533596[284] = 0.0;
   out_8733031835894533596[285] = 1.0;
   out_8733031835894533596[286] = 0.0;
   out_8733031835894533596[287] = 0.0;
   out_8733031835894533596[288] = 0.0;
   out_8733031835894533596[289] = 0.0;
   out_8733031835894533596[290] = 0.0;
   out_8733031835894533596[291] = 0.0;
   out_8733031835894533596[292] = 0.0;
   out_8733031835894533596[293] = 0.0;
   out_8733031835894533596[294] = 0.0;
   out_8733031835894533596[295] = 0.0;
   out_8733031835894533596[296] = 0.0;
   out_8733031835894533596[297] = 0.0;
   out_8733031835894533596[298] = 0.0;
   out_8733031835894533596[299] = 0.0;
   out_8733031835894533596[300] = 0.0;
   out_8733031835894533596[301] = 0.0;
   out_8733031835894533596[302] = 0.0;
   out_8733031835894533596[303] = 0.0;
   out_8733031835894533596[304] = 1.0;
   out_8733031835894533596[305] = 0.0;
   out_8733031835894533596[306] = 0.0;
   out_8733031835894533596[307] = 0.0;
   out_8733031835894533596[308] = 0.0;
   out_8733031835894533596[309] = 0.0;
   out_8733031835894533596[310] = 0.0;
   out_8733031835894533596[311] = 0.0;
   out_8733031835894533596[312] = 0.0;
   out_8733031835894533596[313] = 0.0;
   out_8733031835894533596[314] = 0.0;
   out_8733031835894533596[315] = 0.0;
   out_8733031835894533596[316] = 0.0;
   out_8733031835894533596[317] = 0.0;
   out_8733031835894533596[318] = 0.0;
   out_8733031835894533596[319] = 0.0;
   out_8733031835894533596[320] = 0.0;
   out_8733031835894533596[321] = 0.0;
   out_8733031835894533596[322] = 0.0;
   out_8733031835894533596[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8868616660930423881) {
   out_8868616660930423881[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8868616660930423881[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8868616660930423881[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8868616660930423881[3] = dt*state[12] + state[3];
   out_8868616660930423881[4] = dt*state[13] + state[4];
   out_8868616660930423881[5] = dt*state[14] + state[5];
   out_8868616660930423881[6] = state[6];
   out_8868616660930423881[7] = state[7];
   out_8868616660930423881[8] = state[8];
   out_8868616660930423881[9] = state[9];
   out_8868616660930423881[10] = state[10];
   out_8868616660930423881[11] = state[11];
   out_8868616660930423881[12] = state[12];
   out_8868616660930423881[13] = state[13];
   out_8868616660930423881[14] = state[14];
   out_8868616660930423881[15] = state[15];
   out_8868616660930423881[16] = state[16];
   out_8868616660930423881[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6060136886631410443) {
   out_6060136886631410443[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6060136886631410443[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6060136886631410443[2] = 0;
   out_6060136886631410443[3] = 0;
   out_6060136886631410443[4] = 0;
   out_6060136886631410443[5] = 0;
   out_6060136886631410443[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6060136886631410443[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6060136886631410443[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6060136886631410443[9] = 0;
   out_6060136886631410443[10] = 0;
   out_6060136886631410443[11] = 0;
   out_6060136886631410443[12] = 0;
   out_6060136886631410443[13] = 0;
   out_6060136886631410443[14] = 0;
   out_6060136886631410443[15] = 0;
   out_6060136886631410443[16] = 0;
   out_6060136886631410443[17] = 0;
   out_6060136886631410443[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6060136886631410443[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6060136886631410443[20] = 0;
   out_6060136886631410443[21] = 0;
   out_6060136886631410443[22] = 0;
   out_6060136886631410443[23] = 0;
   out_6060136886631410443[24] = 0;
   out_6060136886631410443[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6060136886631410443[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6060136886631410443[27] = 0;
   out_6060136886631410443[28] = 0;
   out_6060136886631410443[29] = 0;
   out_6060136886631410443[30] = 0;
   out_6060136886631410443[31] = 0;
   out_6060136886631410443[32] = 0;
   out_6060136886631410443[33] = 0;
   out_6060136886631410443[34] = 0;
   out_6060136886631410443[35] = 0;
   out_6060136886631410443[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6060136886631410443[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6060136886631410443[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6060136886631410443[39] = 0;
   out_6060136886631410443[40] = 0;
   out_6060136886631410443[41] = 0;
   out_6060136886631410443[42] = 0;
   out_6060136886631410443[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6060136886631410443[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6060136886631410443[45] = 0;
   out_6060136886631410443[46] = 0;
   out_6060136886631410443[47] = 0;
   out_6060136886631410443[48] = 0;
   out_6060136886631410443[49] = 0;
   out_6060136886631410443[50] = 0;
   out_6060136886631410443[51] = 0;
   out_6060136886631410443[52] = 0;
   out_6060136886631410443[53] = 0;
   out_6060136886631410443[54] = 0;
   out_6060136886631410443[55] = 0;
   out_6060136886631410443[56] = 0;
   out_6060136886631410443[57] = 1;
   out_6060136886631410443[58] = 0;
   out_6060136886631410443[59] = 0;
   out_6060136886631410443[60] = 0;
   out_6060136886631410443[61] = 0;
   out_6060136886631410443[62] = 0;
   out_6060136886631410443[63] = 0;
   out_6060136886631410443[64] = 0;
   out_6060136886631410443[65] = 0;
   out_6060136886631410443[66] = dt;
   out_6060136886631410443[67] = 0;
   out_6060136886631410443[68] = 0;
   out_6060136886631410443[69] = 0;
   out_6060136886631410443[70] = 0;
   out_6060136886631410443[71] = 0;
   out_6060136886631410443[72] = 0;
   out_6060136886631410443[73] = 0;
   out_6060136886631410443[74] = 0;
   out_6060136886631410443[75] = 0;
   out_6060136886631410443[76] = 1;
   out_6060136886631410443[77] = 0;
   out_6060136886631410443[78] = 0;
   out_6060136886631410443[79] = 0;
   out_6060136886631410443[80] = 0;
   out_6060136886631410443[81] = 0;
   out_6060136886631410443[82] = 0;
   out_6060136886631410443[83] = 0;
   out_6060136886631410443[84] = 0;
   out_6060136886631410443[85] = dt;
   out_6060136886631410443[86] = 0;
   out_6060136886631410443[87] = 0;
   out_6060136886631410443[88] = 0;
   out_6060136886631410443[89] = 0;
   out_6060136886631410443[90] = 0;
   out_6060136886631410443[91] = 0;
   out_6060136886631410443[92] = 0;
   out_6060136886631410443[93] = 0;
   out_6060136886631410443[94] = 0;
   out_6060136886631410443[95] = 1;
   out_6060136886631410443[96] = 0;
   out_6060136886631410443[97] = 0;
   out_6060136886631410443[98] = 0;
   out_6060136886631410443[99] = 0;
   out_6060136886631410443[100] = 0;
   out_6060136886631410443[101] = 0;
   out_6060136886631410443[102] = 0;
   out_6060136886631410443[103] = 0;
   out_6060136886631410443[104] = dt;
   out_6060136886631410443[105] = 0;
   out_6060136886631410443[106] = 0;
   out_6060136886631410443[107] = 0;
   out_6060136886631410443[108] = 0;
   out_6060136886631410443[109] = 0;
   out_6060136886631410443[110] = 0;
   out_6060136886631410443[111] = 0;
   out_6060136886631410443[112] = 0;
   out_6060136886631410443[113] = 0;
   out_6060136886631410443[114] = 1;
   out_6060136886631410443[115] = 0;
   out_6060136886631410443[116] = 0;
   out_6060136886631410443[117] = 0;
   out_6060136886631410443[118] = 0;
   out_6060136886631410443[119] = 0;
   out_6060136886631410443[120] = 0;
   out_6060136886631410443[121] = 0;
   out_6060136886631410443[122] = 0;
   out_6060136886631410443[123] = 0;
   out_6060136886631410443[124] = 0;
   out_6060136886631410443[125] = 0;
   out_6060136886631410443[126] = 0;
   out_6060136886631410443[127] = 0;
   out_6060136886631410443[128] = 0;
   out_6060136886631410443[129] = 0;
   out_6060136886631410443[130] = 0;
   out_6060136886631410443[131] = 0;
   out_6060136886631410443[132] = 0;
   out_6060136886631410443[133] = 1;
   out_6060136886631410443[134] = 0;
   out_6060136886631410443[135] = 0;
   out_6060136886631410443[136] = 0;
   out_6060136886631410443[137] = 0;
   out_6060136886631410443[138] = 0;
   out_6060136886631410443[139] = 0;
   out_6060136886631410443[140] = 0;
   out_6060136886631410443[141] = 0;
   out_6060136886631410443[142] = 0;
   out_6060136886631410443[143] = 0;
   out_6060136886631410443[144] = 0;
   out_6060136886631410443[145] = 0;
   out_6060136886631410443[146] = 0;
   out_6060136886631410443[147] = 0;
   out_6060136886631410443[148] = 0;
   out_6060136886631410443[149] = 0;
   out_6060136886631410443[150] = 0;
   out_6060136886631410443[151] = 0;
   out_6060136886631410443[152] = 1;
   out_6060136886631410443[153] = 0;
   out_6060136886631410443[154] = 0;
   out_6060136886631410443[155] = 0;
   out_6060136886631410443[156] = 0;
   out_6060136886631410443[157] = 0;
   out_6060136886631410443[158] = 0;
   out_6060136886631410443[159] = 0;
   out_6060136886631410443[160] = 0;
   out_6060136886631410443[161] = 0;
   out_6060136886631410443[162] = 0;
   out_6060136886631410443[163] = 0;
   out_6060136886631410443[164] = 0;
   out_6060136886631410443[165] = 0;
   out_6060136886631410443[166] = 0;
   out_6060136886631410443[167] = 0;
   out_6060136886631410443[168] = 0;
   out_6060136886631410443[169] = 0;
   out_6060136886631410443[170] = 0;
   out_6060136886631410443[171] = 1;
   out_6060136886631410443[172] = 0;
   out_6060136886631410443[173] = 0;
   out_6060136886631410443[174] = 0;
   out_6060136886631410443[175] = 0;
   out_6060136886631410443[176] = 0;
   out_6060136886631410443[177] = 0;
   out_6060136886631410443[178] = 0;
   out_6060136886631410443[179] = 0;
   out_6060136886631410443[180] = 0;
   out_6060136886631410443[181] = 0;
   out_6060136886631410443[182] = 0;
   out_6060136886631410443[183] = 0;
   out_6060136886631410443[184] = 0;
   out_6060136886631410443[185] = 0;
   out_6060136886631410443[186] = 0;
   out_6060136886631410443[187] = 0;
   out_6060136886631410443[188] = 0;
   out_6060136886631410443[189] = 0;
   out_6060136886631410443[190] = 1;
   out_6060136886631410443[191] = 0;
   out_6060136886631410443[192] = 0;
   out_6060136886631410443[193] = 0;
   out_6060136886631410443[194] = 0;
   out_6060136886631410443[195] = 0;
   out_6060136886631410443[196] = 0;
   out_6060136886631410443[197] = 0;
   out_6060136886631410443[198] = 0;
   out_6060136886631410443[199] = 0;
   out_6060136886631410443[200] = 0;
   out_6060136886631410443[201] = 0;
   out_6060136886631410443[202] = 0;
   out_6060136886631410443[203] = 0;
   out_6060136886631410443[204] = 0;
   out_6060136886631410443[205] = 0;
   out_6060136886631410443[206] = 0;
   out_6060136886631410443[207] = 0;
   out_6060136886631410443[208] = 0;
   out_6060136886631410443[209] = 1;
   out_6060136886631410443[210] = 0;
   out_6060136886631410443[211] = 0;
   out_6060136886631410443[212] = 0;
   out_6060136886631410443[213] = 0;
   out_6060136886631410443[214] = 0;
   out_6060136886631410443[215] = 0;
   out_6060136886631410443[216] = 0;
   out_6060136886631410443[217] = 0;
   out_6060136886631410443[218] = 0;
   out_6060136886631410443[219] = 0;
   out_6060136886631410443[220] = 0;
   out_6060136886631410443[221] = 0;
   out_6060136886631410443[222] = 0;
   out_6060136886631410443[223] = 0;
   out_6060136886631410443[224] = 0;
   out_6060136886631410443[225] = 0;
   out_6060136886631410443[226] = 0;
   out_6060136886631410443[227] = 0;
   out_6060136886631410443[228] = 1;
   out_6060136886631410443[229] = 0;
   out_6060136886631410443[230] = 0;
   out_6060136886631410443[231] = 0;
   out_6060136886631410443[232] = 0;
   out_6060136886631410443[233] = 0;
   out_6060136886631410443[234] = 0;
   out_6060136886631410443[235] = 0;
   out_6060136886631410443[236] = 0;
   out_6060136886631410443[237] = 0;
   out_6060136886631410443[238] = 0;
   out_6060136886631410443[239] = 0;
   out_6060136886631410443[240] = 0;
   out_6060136886631410443[241] = 0;
   out_6060136886631410443[242] = 0;
   out_6060136886631410443[243] = 0;
   out_6060136886631410443[244] = 0;
   out_6060136886631410443[245] = 0;
   out_6060136886631410443[246] = 0;
   out_6060136886631410443[247] = 1;
   out_6060136886631410443[248] = 0;
   out_6060136886631410443[249] = 0;
   out_6060136886631410443[250] = 0;
   out_6060136886631410443[251] = 0;
   out_6060136886631410443[252] = 0;
   out_6060136886631410443[253] = 0;
   out_6060136886631410443[254] = 0;
   out_6060136886631410443[255] = 0;
   out_6060136886631410443[256] = 0;
   out_6060136886631410443[257] = 0;
   out_6060136886631410443[258] = 0;
   out_6060136886631410443[259] = 0;
   out_6060136886631410443[260] = 0;
   out_6060136886631410443[261] = 0;
   out_6060136886631410443[262] = 0;
   out_6060136886631410443[263] = 0;
   out_6060136886631410443[264] = 0;
   out_6060136886631410443[265] = 0;
   out_6060136886631410443[266] = 1;
   out_6060136886631410443[267] = 0;
   out_6060136886631410443[268] = 0;
   out_6060136886631410443[269] = 0;
   out_6060136886631410443[270] = 0;
   out_6060136886631410443[271] = 0;
   out_6060136886631410443[272] = 0;
   out_6060136886631410443[273] = 0;
   out_6060136886631410443[274] = 0;
   out_6060136886631410443[275] = 0;
   out_6060136886631410443[276] = 0;
   out_6060136886631410443[277] = 0;
   out_6060136886631410443[278] = 0;
   out_6060136886631410443[279] = 0;
   out_6060136886631410443[280] = 0;
   out_6060136886631410443[281] = 0;
   out_6060136886631410443[282] = 0;
   out_6060136886631410443[283] = 0;
   out_6060136886631410443[284] = 0;
   out_6060136886631410443[285] = 1;
   out_6060136886631410443[286] = 0;
   out_6060136886631410443[287] = 0;
   out_6060136886631410443[288] = 0;
   out_6060136886631410443[289] = 0;
   out_6060136886631410443[290] = 0;
   out_6060136886631410443[291] = 0;
   out_6060136886631410443[292] = 0;
   out_6060136886631410443[293] = 0;
   out_6060136886631410443[294] = 0;
   out_6060136886631410443[295] = 0;
   out_6060136886631410443[296] = 0;
   out_6060136886631410443[297] = 0;
   out_6060136886631410443[298] = 0;
   out_6060136886631410443[299] = 0;
   out_6060136886631410443[300] = 0;
   out_6060136886631410443[301] = 0;
   out_6060136886631410443[302] = 0;
   out_6060136886631410443[303] = 0;
   out_6060136886631410443[304] = 1;
   out_6060136886631410443[305] = 0;
   out_6060136886631410443[306] = 0;
   out_6060136886631410443[307] = 0;
   out_6060136886631410443[308] = 0;
   out_6060136886631410443[309] = 0;
   out_6060136886631410443[310] = 0;
   out_6060136886631410443[311] = 0;
   out_6060136886631410443[312] = 0;
   out_6060136886631410443[313] = 0;
   out_6060136886631410443[314] = 0;
   out_6060136886631410443[315] = 0;
   out_6060136886631410443[316] = 0;
   out_6060136886631410443[317] = 0;
   out_6060136886631410443[318] = 0;
   out_6060136886631410443[319] = 0;
   out_6060136886631410443[320] = 0;
   out_6060136886631410443[321] = 0;
   out_6060136886631410443[322] = 0;
   out_6060136886631410443[323] = 1;
}
void h_4(double *state, double *unused, double *out_6022306051754618176) {
   out_6022306051754618176[0] = state[6] + state[9];
   out_6022306051754618176[1] = state[7] + state[10];
   out_6022306051754618176[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5164396188455542) {
   out_5164396188455542[0] = 0;
   out_5164396188455542[1] = 0;
   out_5164396188455542[2] = 0;
   out_5164396188455542[3] = 0;
   out_5164396188455542[4] = 0;
   out_5164396188455542[5] = 0;
   out_5164396188455542[6] = 1;
   out_5164396188455542[7] = 0;
   out_5164396188455542[8] = 0;
   out_5164396188455542[9] = 1;
   out_5164396188455542[10] = 0;
   out_5164396188455542[11] = 0;
   out_5164396188455542[12] = 0;
   out_5164396188455542[13] = 0;
   out_5164396188455542[14] = 0;
   out_5164396188455542[15] = 0;
   out_5164396188455542[16] = 0;
   out_5164396188455542[17] = 0;
   out_5164396188455542[18] = 0;
   out_5164396188455542[19] = 0;
   out_5164396188455542[20] = 0;
   out_5164396188455542[21] = 0;
   out_5164396188455542[22] = 0;
   out_5164396188455542[23] = 0;
   out_5164396188455542[24] = 0;
   out_5164396188455542[25] = 1;
   out_5164396188455542[26] = 0;
   out_5164396188455542[27] = 0;
   out_5164396188455542[28] = 1;
   out_5164396188455542[29] = 0;
   out_5164396188455542[30] = 0;
   out_5164396188455542[31] = 0;
   out_5164396188455542[32] = 0;
   out_5164396188455542[33] = 0;
   out_5164396188455542[34] = 0;
   out_5164396188455542[35] = 0;
   out_5164396188455542[36] = 0;
   out_5164396188455542[37] = 0;
   out_5164396188455542[38] = 0;
   out_5164396188455542[39] = 0;
   out_5164396188455542[40] = 0;
   out_5164396188455542[41] = 0;
   out_5164396188455542[42] = 0;
   out_5164396188455542[43] = 0;
   out_5164396188455542[44] = 1;
   out_5164396188455542[45] = 0;
   out_5164396188455542[46] = 0;
   out_5164396188455542[47] = 1;
   out_5164396188455542[48] = 0;
   out_5164396188455542[49] = 0;
   out_5164396188455542[50] = 0;
   out_5164396188455542[51] = 0;
   out_5164396188455542[52] = 0;
   out_5164396188455542[53] = 0;
}
void h_10(double *state, double *unused, double *out_7686741891596612442) {
   out_7686741891596612442[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7686741891596612442[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7686741891596612442[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6739799969353632287) {
   out_6739799969353632287[0] = 0;
   out_6739799969353632287[1] = 9.8100000000000005*cos(state[1]);
   out_6739799969353632287[2] = 0;
   out_6739799969353632287[3] = 0;
   out_6739799969353632287[4] = -state[8];
   out_6739799969353632287[5] = state[7];
   out_6739799969353632287[6] = 0;
   out_6739799969353632287[7] = state[5];
   out_6739799969353632287[8] = -state[4];
   out_6739799969353632287[9] = 0;
   out_6739799969353632287[10] = 0;
   out_6739799969353632287[11] = 0;
   out_6739799969353632287[12] = 1;
   out_6739799969353632287[13] = 0;
   out_6739799969353632287[14] = 0;
   out_6739799969353632287[15] = 1;
   out_6739799969353632287[16] = 0;
   out_6739799969353632287[17] = 0;
   out_6739799969353632287[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6739799969353632287[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6739799969353632287[20] = 0;
   out_6739799969353632287[21] = state[8];
   out_6739799969353632287[22] = 0;
   out_6739799969353632287[23] = -state[6];
   out_6739799969353632287[24] = -state[5];
   out_6739799969353632287[25] = 0;
   out_6739799969353632287[26] = state[3];
   out_6739799969353632287[27] = 0;
   out_6739799969353632287[28] = 0;
   out_6739799969353632287[29] = 0;
   out_6739799969353632287[30] = 0;
   out_6739799969353632287[31] = 1;
   out_6739799969353632287[32] = 0;
   out_6739799969353632287[33] = 0;
   out_6739799969353632287[34] = 1;
   out_6739799969353632287[35] = 0;
   out_6739799969353632287[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6739799969353632287[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6739799969353632287[38] = 0;
   out_6739799969353632287[39] = -state[7];
   out_6739799969353632287[40] = state[6];
   out_6739799969353632287[41] = 0;
   out_6739799969353632287[42] = state[4];
   out_6739799969353632287[43] = -state[3];
   out_6739799969353632287[44] = 0;
   out_6739799969353632287[45] = 0;
   out_6739799969353632287[46] = 0;
   out_6739799969353632287[47] = 0;
   out_6739799969353632287[48] = 0;
   out_6739799969353632287[49] = 0;
   out_6739799969353632287[50] = 1;
   out_6739799969353632287[51] = 0;
   out_6739799969353632287[52] = 0;
   out_6739799969353632287[53] = 1;
}
void h_13(double *state, double *unused, double *out_2333214722145795372) {
   out_2333214722145795372[0] = state[3];
   out_2333214722145795372[1] = state[4];
   out_2333214722145795372[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3217438221520788343) {
   out_3217438221520788343[0] = 0;
   out_3217438221520788343[1] = 0;
   out_3217438221520788343[2] = 0;
   out_3217438221520788343[3] = 1;
   out_3217438221520788343[4] = 0;
   out_3217438221520788343[5] = 0;
   out_3217438221520788343[6] = 0;
   out_3217438221520788343[7] = 0;
   out_3217438221520788343[8] = 0;
   out_3217438221520788343[9] = 0;
   out_3217438221520788343[10] = 0;
   out_3217438221520788343[11] = 0;
   out_3217438221520788343[12] = 0;
   out_3217438221520788343[13] = 0;
   out_3217438221520788343[14] = 0;
   out_3217438221520788343[15] = 0;
   out_3217438221520788343[16] = 0;
   out_3217438221520788343[17] = 0;
   out_3217438221520788343[18] = 0;
   out_3217438221520788343[19] = 0;
   out_3217438221520788343[20] = 0;
   out_3217438221520788343[21] = 0;
   out_3217438221520788343[22] = 1;
   out_3217438221520788343[23] = 0;
   out_3217438221520788343[24] = 0;
   out_3217438221520788343[25] = 0;
   out_3217438221520788343[26] = 0;
   out_3217438221520788343[27] = 0;
   out_3217438221520788343[28] = 0;
   out_3217438221520788343[29] = 0;
   out_3217438221520788343[30] = 0;
   out_3217438221520788343[31] = 0;
   out_3217438221520788343[32] = 0;
   out_3217438221520788343[33] = 0;
   out_3217438221520788343[34] = 0;
   out_3217438221520788343[35] = 0;
   out_3217438221520788343[36] = 0;
   out_3217438221520788343[37] = 0;
   out_3217438221520788343[38] = 0;
   out_3217438221520788343[39] = 0;
   out_3217438221520788343[40] = 0;
   out_3217438221520788343[41] = 1;
   out_3217438221520788343[42] = 0;
   out_3217438221520788343[43] = 0;
   out_3217438221520788343[44] = 0;
   out_3217438221520788343[45] = 0;
   out_3217438221520788343[46] = 0;
   out_3217438221520788343[47] = 0;
   out_3217438221520788343[48] = 0;
   out_3217438221520788343[49] = 0;
   out_3217438221520788343[50] = 0;
   out_3217438221520788343[51] = 0;
   out_3217438221520788343[52] = 0;
   out_3217438221520788343[53] = 0;
}
void h_14(double *state, double *unused, double *out_2463064256028585948) {
   out_2463064256028585948[0] = state[6];
   out_2463064256028585948[1] = state[7];
   out_2463064256028585948[2] = state[8];
}
void H_14(double *state, double *unused, double *out_429952130456428057) {
   out_429952130456428057[0] = 0;
   out_429952130456428057[1] = 0;
   out_429952130456428057[2] = 0;
   out_429952130456428057[3] = 0;
   out_429952130456428057[4] = 0;
   out_429952130456428057[5] = 0;
   out_429952130456428057[6] = 1;
   out_429952130456428057[7] = 0;
   out_429952130456428057[8] = 0;
   out_429952130456428057[9] = 0;
   out_429952130456428057[10] = 0;
   out_429952130456428057[11] = 0;
   out_429952130456428057[12] = 0;
   out_429952130456428057[13] = 0;
   out_429952130456428057[14] = 0;
   out_429952130456428057[15] = 0;
   out_429952130456428057[16] = 0;
   out_429952130456428057[17] = 0;
   out_429952130456428057[18] = 0;
   out_429952130456428057[19] = 0;
   out_429952130456428057[20] = 0;
   out_429952130456428057[21] = 0;
   out_429952130456428057[22] = 0;
   out_429952130456428057[23] = 0;
   out_429952130456428057[24] = 0;
   out_429952130456428057[25] = 1;
   out_429952130456428057[26] = 0;
   out_429952130456428057[27] = 0;
   out_429952130456428057[28] = 0;
   out_429952130456428057[29] = 0;
   out_429952130456428057[30] = 0;
   out_429952130456428057[31] = 0;
   out_429952130456428057[32] = 0;
   out_429952130456428057[33] = 0;
   out_429952130456428057[34] = 0;
   out_429952130456428057[35] = 0;
   out_429952130456428057[36] = 0;
   out_429952130456428057[37] = 0;
   out_429952130456428057[38] = 0;
   out_429952130456428057[39] = 0;
   out_429952130456428057[40] = 0;
   out_429952130456428057[41] = 0;
   out_429952130456428057[42] = 0;
   out_429952130456428057[43] = 0;
   out_429952130456428057[44] = 1;
   out_429952130456428057[45] = 0;
   out_429952130456428057[46] = 0;
   out_429952130456428057[47] = 0;
   out_429952130456428057[48] = 0;
   out_429952130456428057[49] = 0;
   out_429952130456428057[50] = 0;
   out_429952130456428057[51] = 0;
   out_429952130456428057[52] = 0;
   out_429952130456428057[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4574623741916747896) {
  err_fun(nom_x, delta_x, out_4574623741916747896);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2341160614075288752) {
  inv_err_fun(nom_x, true_x, out_2341160614075288752);
}
void pose_H_mod_fun(double *state, double *out_8733031835894533596) {
  H_mod_fun(state, out_8733031835894533596);
}
void pose_f_fun(double *state, double dt, double *out_8868616660930423881) {
  f_fun(state,  dt, out_8868616660930423881);
}
void pose_F_fun(double *state, double dt, double *out_6060136886631410443) {
  F_fun(state,  dt, out_6060136886631410443);
}
void pose_h_4(double *state, double *unused, double *out_6022306051754618176) {
  h_4(state, unused, out_6022306051754618176);
}
void pose_H_4(double *state, double *unused, double *out_5164396188455542) {
  H_4(state, unused, out_5164396188455542);
}
void pose_h_10(double *state, double *unused, double *out_7686741891596612442) {
  h_10(state, unused, out_7686741891596612442);
}
void pose_H_10(double *state, double *unused, double *out_6739799969353632287) {
  H_10(state, unused, out_6739799969353632287);
}
void pose_h_13(double *state, double *unused, double *out_2333214722145795372) {
  h_13(state, unused, out_2333214722145795372);
}
void pose_H_13(double *state, double *unused, double *out_3217438221520788343) {
  H_13(state, unused, out_3217438221520788343);
}
void pose_h_14(double *state, double *unused, double *out_2463064256028585948) {
  h_14(state, unused, out_2463064256028585948);
}
void pose_H_14(double *state, double *unused, double *out_429952130456428057) {
  H_14(state, unused, out_429952130456428057);
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
