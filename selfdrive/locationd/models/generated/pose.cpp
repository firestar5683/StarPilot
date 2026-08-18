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
void err_fun(double *nom_x, double *delta_x, double *out_3597460724364137401) {
   out_3597460724364137401[0] = delta_x[0] + nom_x[0];
   out_3597460724364137401[1] = delta_x[1] + nom_x[1];
   out_3597460724364137401[2] = delta_x[2] + nom_x[2];
   out_3597460724364137401[3] = delta_x[3] + nom_x[3];
   out_3597460724364137401[4] = delta_x[4] + nom_x[4];
   out_3597460724364137401[5] = delta_x[5] + nom_x[5];
   out_3597460724364137401[6] = delta_x[6] + nom_x[6];
   out_3597460724364137401[7] = delta_x[7] + nom_x[7];
   out_3597460724364137401[8] = delta_x[8] + nom_x[8];
   out_3597460724364137401[9] = delta_x[9] + nom_x[9];
   out_3597460724364137401[10] = delta_x[10] + nom_x[10];
   out_3597460724364137401[11] = delta_x[11] + nom_x[11];
   out_3597460724364137401[12] = delta_x[12] + nom_x[12];
   out_3597460724364137401[13] = delta_x[13] + nom_x[13];
   out_3597460724364137401[14] = delta_x[14] + nom_x[14];
   out_3597460724364137401[15] = delta_x[15] + nom_x[15];
   out_3597460724364137401[16] = delta_x[16] + nom_x[16];
   out_3597460724364137401[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1062002485999931142) {
   out_1062002485999931142[0] = -nom_x[0] + true_x[0];
   out_1062002485999931142[1] = -nom_x[1] + true_x[1];
   out_1062002485999931142[2] = -nom_x[2] + true_x[2];
   out_1062002485999931142[3] = -nom_x[3] + true_x[3];
   out_1062002485999931142[4] = -nom_x[4] + true_x[4];
   out_1062002485999931142[5] = -nom_x[5] + true_x[5];
   out_1062002485999931142[6] = -nom_x[6] + true_x[6];
   out_1062002485999931142[7] = -nom_x[7] + true_x[7];
   out_1062002485999931142[8] = -nom_x[8] + true_x[8];
   out_1062002485999931142[9] = -nom_x[9] + true_x[9];
   out_1062002485999931142[10] = -nom_x[10] + true_x[10];
   out_1062002485999931142[11] = -nom_x[11] + true_x[11];
   out_1062002485999931142[12] = -nom_x[12] + true_x[12];
   out_1062002485999931142[13] = -nom_x[13] + true_x[13];
   out_1062002485999931142[14] = -nom_x[14] + true_x[14];
   out_1062002485999931142[15] = -nom_x[15] + true_x[15];
   out_1062002485999931142[16] = -nom_x[16] + true_x[16];
   out_1062002485999931142[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4662972867475177241) {
   out_4662972867475177241[0] = 1.0;
   out_4662972867475177241[1] = 0.0;
   out_4662972867475177241[2] = 0.0;
   out_4662972867475177241[3] = 0.0;
   out_4662972867475177241[4] = 0.0;
   out_4662972867475177241[5] = 0.0;
   out_4662972867475177241[6] = 0.0;
   out_4662972867475177241[7] = 0.0;
   out_4662972867475177241[8] = 0.0;
   out_4662972867475177241[9] = 0.0;
   out_4662972867475177241[10] = 0.0;
   out_4662972867475177241[11] = 0.0;
   out_4662972867475177241[12] = 0.0;
   out_4662972867475177241[13] = 0.0;
   out_4662972867475177241[14] = 0.0;
   out_4662972867475177241[15] = 0.0;
   out_4662972867475177241[16] = 0.0;
   out_4662972867475177241[17] = 0.0;
   out_4662972867475177241[18] = 0.0;
   out_4662972867475177241[19] = 1.0;
   out_4662972867475177241[20] = 0.0;
   out_4662972867475177241[21] = 0.0;
   out_4662972867475177241[22] = 0.0;
   out_4662972867475177241[23] = 0.0;
   out_4662972867475177241[24] = 0.0;
   out_4662972867475177241[25] = 0.0;
   out_4662972867475177241[26] = 0.0;
   out_4662972867475177241[27] = 0.0;
   out_4662972867475177241[28] = 0.0;
   out_4662972867475177241[29] = 0.0;
   out_4662972867475177241[30] = 0.0;
   out_4662972867475177241[31] = 0.0;
   out_4662972867475177241[32] = 0.0;
   out_4662972867475177241[33] = 0.0;
   out_4662972867475177241[34] = 0.0;
   out_4662972867475177241[35] = 0.0;
   out_4662972867475177241[36] = 0.0;
   out_4662972867475177241[37] = 0.0;
   out_4662972867475177241[38] = 1.0;
   out_4662972867475177241[39] = 0.0;
   out_4662972867475177241[40] = 0.0;
   out_4662972867475177241[41] = 0.0;
   out_4662972867475177241[42] = 0.0;
   out_4662972867475177241[43] = 0.0;
   out_4662972867475177241[44] = 0.0;
   out_4662972867475177241[45] = 0.0;
   out_4662972867475177241[46] = 0.0;
   out_4662972867475177241[47] = 0.0;
   out_4662972867475177241[48] = 0.0;
   out_4662972867475177241[49] = 0.0;
   out_4662972867475177241[50] = 0.0;
   out_4662972867475177241[51] = 0.0;
   out_4662972867475177241[52] = 0.0;
   out_4662972867475177241[53] = 0.0;
   out_4662972867475177241[54] = 0.0;
   out_4662972867475177241[55] = 0.0;
   out_4662972867475177241[56] = 0.0;
   out_4662972867475177241[57] = 1.0;
   out_4662972867475177241[58] = 0.0;
   out_4662972867475177241[59] = 0.0;
   out_4662972867475177241[60] = 0.0;
   out_4662972867475177241[61] = 0.0;
   out_4662972867475177241[62] = 0.0;
   out_4662972867475177241[63] = 0.0;
   out_4662972867475177241[64] = 0.0;
   out_4662972867475177241[65] = 0.0;
   out_4662972867475177241[66] = 0.0;
   out_4662972867475177241[67] = 0.0;
   out_4662972867475177241[68] = 0.0;
   out_4662972867475177241[69] = 0.0;
   out_4662972867475177241[70] = 0.0;
   out_4662972867475177241[71] = 0.0;
   out_4662972867475177241[72] = 0.0;
   out_4662972867475177241[73] = 0.0;
   out_4662972867475177241[74] = 0.0;
   out_4662972867475177241[75] = 0.0;
   out_4662972867475177241[76] = 1.0;
   out_4662972867475177241[77] = 0.0;
   out_4662972867475177241[78] = 0.0;
   out_4662972867475177241[79] = 0.0;
   out_4662972867475177241[80] = 0.0;
   out_4662972867475177241[81] = 0.0;
   out_4662972867475177241[82] = 0.0;
   out_4662972867475177241[83] = 0.0;
   out_4662972867475177241[84] = 0.0;
   out_4662972867475177241[85] = 0.0;
   out_4662972867475177241[86] = 0.0;
   out_4662972867475177241[87] = 0.0;
   out_4662972867475177241[88] = 0.0;
   out_4662972867475177241[89] = 0.0;
   out_4662972867475177241[90] = 0.0;
   out_4662972867475177241[91] = 0.0;
   out_4662972867475177241[92] = 0.0;
   out_4662972867475177241[93] = 0.0;
   out_4662972867475177241[94] = 0.0;
   out_4662972867475177241[95] = 1.0;
   out_4662972867475177241[96] = 0.0;
   out_4662972867475177241[97] = 0.0;
   out_4662972867475177241[98] = 0.0;
   out_4662972867475177241[99] = 0.0;
   out_4662972867475177241[100] = 0.0;
   out_4662972867475177241[101] = 0.0;
   out_4662972867475177241[102] = 0.0;
   out_4662972867475177241[103] = 0.0;
   out_4662972867475177241[104] = 0.0;
   out_4662972867475177241[105] = 0.0;
   out_4662972867475177241[106] = 0.0;
   out_4662972867475177241[107] = 0.0;
   out_4662972867475177241[108] = 0.0;
   out_4662972867475177241[109] = 0.0;
   out_4662972867475177241[110] = 0.0;
   out_4662972867475177241[111] = 0.0;
   out_4662972867475177241[112] = 0.0;
   out_4662972867475177241[113] = 0.0;
   out_4662972867475177241[114] = 1.0;
   out_4662972867475177241[115] = 0.0;
   out_4662972867475177241[116] = 0.0;
   out_4662972867475177241[117] = 0.0;
   out_4662972867475177241[118] = 0.0;
   out_4662972867475177241[119] = 0.0;
   out_4662972867475177241[120] = 0.0;
   out_4662972867475177241[121] = 0.0;
   out_4662972867475177241[122] = 0.0;
   out_4662972867475177241[123] = 0.0;
   out_4662972867475177241[124] = 0.0;
   out_4662972867475177241[125] = 0.0;
   out_4662972867475177241[126] = 0.0;
   out_4662972867475177241[127] = 0.0;
   out_4662972867475177241[128] = 0.0;
   out_4662972867475177241[129] = 0.0;
   out_4662972867475177241[130] = 0.0;
   out_4662972867475177241[131] = 0.0;
   out_4662972867475177241[132] = 0.0;
   out_4662972867475177241[133] = 1.0;
   out_4662972867475177241[134] = 0.0;
   out_4662972867475177241[135] = 0.0;
   out_4662972867475177241[136] = 0.0;
   out_4662972867475177241[137] = 0.0;
   out_4662972867475177241[138] = 0.0;
   out_4662972867475177241[139] = 0.0;
   out_4662972867475177241[140] = 0.0;
   out_4662972867475177241[141] = 0.0;
   out_4662972867475177241[142] = 0.0;
   out_4662972867475177241[143] = 0.0;
   out_4662972867475177241[144] = 0.0;
   out_4662972867475177241[145] = 0.0;
   out_4662972867475177241[146] = 0.0;
   out_4662972867475177241[147] = 0.0;
   out_4662972867475177241[148] = 0.0;
   out_4662972867475177241[149] = 0.0;
   out_4662972867475177241[150] = 0.0;
   out_4662972867475177241[151] = 0.0;
   out_4662972867475177241[152] = 1.0;
   out_4662972867475177241[153] = 0.0;
   out_4662972867475177241[154] = 0.0;
   out_4662972867475177241[155] = 0.0;
   out_4662972867475177241[156] = 0.0;
   out_4662972867475177241[157] = 0.0;
   out_4662972867475177241[158] = 0.0;
   out_4662972867475177241[159] = 0.0;
   out_4662972867475177241[160] = 0.0;
   out_4662972867475177241[161] = 0.0;
   out_4662972867475177241[162] = 0.0;
   out_4662972867475177241[163] = 0.0;
   out_4662972867475177241[164] = 0.0;
   out_4662972867475177241[165] = 0.0;
   out_4662972867475177241[166] = 0.0;
   out_4662972867475177241[167] = 0.0;
   out_4662972867475177241[168] = 0.0;
   out_4662972867475177241[169] = 0.0;
   out_4662972867475177241[170] = 0.0;
   out_4662972867475177241[171] = 1.0;
   out_4662972867475177241[172] = 0.0;
   out_4662972867475177241[173] = 0.0;
   out_4662972867475177241[174] = 0.0;
   out_4662972867475177241[175] = 0.0;
   out_4662972867475177241[176] = 0.0;
   out_4662972867475177241[177] = 0.0;
   out_4662972867475177241[178] = 0.0;
   out_4662972867475177241[179] = 0.0;
   out_4662972867475177241[180] = 0.0;
   out_4662972867475177241[181] = 0.0;
   out_4662972867475177241[182] = 0.0;
   out_4662972867475177241[183] = 0.0;
   out_4662972867475177241[184] = 0.0;
   out_4662972867475177241[185] = 0.0;
   out_4662972867475177241[186] = 0.0;
   out_4662972867475177241[187] = 0.0;
   out_4662972867475177241[188] = 0.0;
   out_4662972867475177241[189] = 0.0;
   out_4662972867475177241[190] = 1.0;
   out_4662972867475177241[191] = 0.0;
   out_4662972867475177241[192] = 0.0;
   out_4662972867475177241[193] = 0.0;
   out_4662972867475177241[194] = 0.0;
   out_4662972867475177241[195] = 0.0;
   out_4662972867475177241[196] = 0.0;
   out_4662972867475177241[197] = 0.0;
   out_4662972867475177241[198] = 0.0;
   out_4662972867475177241[199] = 0.0;
   out_4662972867475177241[200] = 0.0;
   out_4662972867475177241[201] = 0.0;
   out_4662972867475177241[202] = 0.0;
   out_4662972867475177241[203] = 0.0;
   out_4662972867475177241[204] = 0.0;
   out_4662972867475177241[205] = 0.0;
   out_4662972867475177241[206] = 0.0;
   out_4662972867475177241[207] = 0.0;
   out_4662972867475177241[208] = 0.0;
   out_4662972867475177241[209] = 1.0;
   out_4662972867475177241[210] = 0.0;
   out_4662972867475177241[211] = 0.0;
   out_4662972867475177241[212] = 0.0;
   out_4662972867475177241[213] = 0.0;
   out_4662972867475177241[214] = 0.0;
   out_4662972867475177241[215] = 0.0;
   out_4662972867475177241[216] = 0.0;
   out_4662972867475177241[217] = 0.0;
   out_4662972867475177241[218] = 0.0;
   out_4662972867475177241[219] = 0.0;
   out_4662972867475177241[220] = 0.0;
   out_4662972867475177241[221] = 0.0;
   out_4662972867475177241[222] = 0.0;
   out_4662972867475177241[223] = 0.0;
   out_4662972867475177241[224] = 0.0;
   out_4662972867475177241[225] = 0.0;
   out_4662972867475177241[226] = 0.0;
   out_4662972867475177241[227] = 0.0;
   out_4662972867475177241[228] = 1.0;
   out_4662972867475177241[229] = 0.0;
   out_4662972867475177241[230] = 0.0;
   out_4662972867475177241[231] = 0.0;
   out_4662972867475177241[232] = 0.0;
   out_4662972867475177241[233] = 0.0;
   out_4662972867475177241[234] = 0.0;
   out_4662972867475177241[235] = 0.0;
   out_4662972867475177241[236] = 0.0;
   out_4662972867475177241[237] = 0.0;
   out_4662972867475177241[238] = 0.0;
   out_4662972867475177241[239] = 0.0;
   out_4662972867475177241[240] = 0.0;
   out_4662972867475177241[241] = 0.0;
   out_4662972867475177241[242] = 0.0;
   out_4662972867475177241[243] = 0.0;
   out_4662972867475177241[244] = 0.0;
   out_4662972867475177241[245] = 0.0;
   out_4662972867475177241[246] = 0.0;
   out_4662972867475177241[247] = 1.0;
   out_4662972867475177241[248] = 0.0;
   out_4662972867475177241[249] = 0.0;
   out_4662972867475177241[250] = 0.0;
   out_4662972867475177241[251] = 0.0;
   out_4662972867475177241[252] = 0.0;
   out_4662972867475177241[253] = 0.0;
   out_4662972867475177241[254] = 0.0;
   out_4662972867475177241[255] = 0.0;
   out_4662972867475177241[256] = 0.0;
   out_4662972867475177241[257] = 0.0;
   out_4662972867475177241[258] = 0.0;
   out_4662972867475177241[259] = 0.0;
   out_4662972867475177241[260] = 0.0;
   out_4662972867475177241[261] = 0.0;
   out_4662972867475177241[262] = 0.0;
   out_4662972867475177241[263] = 0.0;
   out_4662972867475177241[264] = 0.0;
   out_4662972867475177241[265] = 0.0;
   out_4662972867475177241[266] = 1.0;
   out_4662972867475177241[267] = 0.0;
   out_4662972867475177241[268] = 0.0;
   out_4662972867475177241[269] = 0.0;
   out_4662972867475177241[270] = 0.0;
   out_4662972867475177241[271] = 0.0;
   out_4662972867475177241[272] = 0.0;
   out_4662972867475177241[273] = 0.0;
   out_4662972867475177241[274] = 0.0;
   out_4662972867475177241[275] = 0.0;
   out_4662972867475177241[276] = 0.0;
   out_4662972867475177241[277] = 0.0;
   out_4662972867475177241[278] = 0.0;
   out_4662972867475177241[279] = 0.0;
   out_4662972867475177241[280] = 0.0;
   out_4662972867475177241[281] = 0.0;
   out_4662972867475177241[282] = 0.0;
   out_4662972867475177241[283] = 0.0;
   out_4662972867475177241[284] = 0.0;
   out_4662972867475177241[285] = 1.0;
   out_4662972867475177241[286] = 0.0;
   out_4662972867475177241[287] = 0.0;
   out_4662972867475177241[288] = 0.0;
   out_4662972867475177241[289] = 0.0;
   out_4662972867475177241[290] = 0.0;
   out_4662972867475177241[291] = 0.0;
   out_4662972867475177241[292] = 0.0;
   out_4662972867475177241[293] = 0.0;
   out_4662972867475177241[294] = 0.0;
   out_4662972867475177241[295] = 0.0;
   out_4662972867475177241[296] = 0.0;
   out_4662972867475177241[297] = 0.0;
   out_4662972867475177241[298] = 0.0;
   out_4662972867475177241[299] = 0.0;
   out_4662972867475177241[300] = 0.0;
   out_4662972867475177241[301] = 0.0;
   out_4662972867475177241[302] = 0.0;
   out_4662972867475177241[303] = 0.0;
   out_4662972867475177241[304] = 1.0;
   out_4662972867475177241[305] = 0.0;
   out_4662972867475177241[306] = 0.0;
   out_4662972867475177241[307] = 0.0;
   out_4662972867475177241[308] = 0.0;
   out_4662972867475177241[309] = 0.0;
   out_4662972867475177241[310] = 0.0;
   out_4662972867475177241[311] = 0.0;
   out_4662972867475177241[312] = 0.0;
   out_4662972867475177241[313] = 0.0;
   out_4662972867475177241[314] = 0.0;
   out_4662972867475177241[315] = 0.0;
   out_4662972867475177241[316] = 0.0;
   out_4662972867475177241[317] = 0.0;
   out_4662972867475177241[318] = 0.0;
   out_4662972867475177241[319] = 0.0;
   out_4662972867475177241[320] = 0.0;
   out_4662972867475177241[321] = 0.0;
   out_4662972867475177241[322] = 0.0;
   out_4662972867475177241[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3840229658681249647) {
   out_3840229658681249647[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3840229658681249647[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3840229658681249647[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3840229658681249647[3] = dt*state[12] + state[3];
   out_3840229658681249647[4] = dt*state[13] + state[4];
   out_3840229658681249647[5] = dt*state[14] + state[5];
   out_3840229658681249647[6] = state[6];
   out_3840229658681249647[7] = state[7];
   out_3840229658681249647[8] = state[8];
   out_3840229658681249647[9] = state[9];
   out_3840229658681249647[10] = state[10];
   out_3840229658681249647[11] = state[11];
   out_3840229658681249647[12] = state[12];
   out_3840229658681249647[13] = state[13];
   out_3840229658681249647[14] = state[14];
   out_3840229658681249647[15] = state[15];
   out_3840229658681249647[16] = state[16];
   out_3840229658681249647[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8220635292339759608) {
   out_8220635292339759608[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8220635292339759608[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8220635292339759608[2] = 0;
   out_8220635292339759608[3] = 0;
   out_8220635292339759608[4] = 0;
   out_8220635292339759608[5] = 0;
   out_8220635292339759608[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8220635292339759608[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8220635292339759608[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8220635292339759608[9] = 0;
   out_8220635292339759608[10] = 0;
   out_8220635292339759608[11] = 0;
   out_8220635292339759608[12] = 0;
   out_8220635292339759608[13] = 0;
   out_8220635292339759608[14] = 0;
   out_8220635292339759608[15] = 0;
   out_8220635292339759608[16] = 0;
   out_8220635292339759608[17] = 0;
   out_8220635292339759608[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8220635292339759608[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8220635292339759608[20] = 0;
   out_8220635292339759608[21] = 0;
   out_8220635292339759608[22] = 0;
   out_8220635292339759608[23] = 0;
   out_8220635292339759608[24] = 0;
   out_8220635292339759608[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8220635292339759608[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8220635292339759608[27] = 0;
   out_8220635292339759608[28] = 0;
   out_8220635292339759608[29] = 0;
   out_8220635292339759608[30] = 0;
   out_8220635292339759608[31] = 0;
   out_8220635292339759608[32] = 0;
   out_8220635292339759608[33] = 0;
   out_8220635292339759608[34] = 0;
   out_8220635292339759608[35] = 0;
   out_8220635292339759608[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8220635292339759608[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8220635292339759608[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8220635292339759608[39] = 0;
   out_8220635292339759608[40] = 0;
   out_8220635292339759608[41] = 0;
   out_8220635292339759608[42] = 0;
   out_8220635292339759608[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8220635292339759608[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8220635292339759608[45] = 0;
   out_8220635292339759608[46] = 0;
   out_8220635292339759608[47] = 0;
   out_8220635292339759608[48] = 0;
   out_8220635292339759608[49] = 0;
   out_8220635292339759608[50] = 0;
   out_8220635292339759608[51] = 0;
   out_8220635292339759608[52] = 0;
   out_8220635292339759608[53] = 0;
   out_8220635292339759608[54] = 0;
   out_8220635292339759608[55] = 0;
   out_8220635292339759608[56] = 0;
   out_8220635292339759608[57] = 1;
   out_8220635292339759608[58] = 0;
   out_8220635292339759608[59] = 0;
   out_8220635292339759608[60] = 0;
   out_8220635292339759608[61] = 0;
   out_8220635292339759608[62] = 0;
   out_8220635292339759608[63] = 0;
   out_8220635292339759608[64] = 0;
   out_8220635292339759608[65] = 0;
   out_8220635292339759608[66] = dt;
   out_8220635292339759608[67] = 0;
   out_8220635292339759608[68] = 0;
   out_8220635292339759608[69] = 0;
   out_8220635292339759608[70] = 0;
   out_8220635292339759608[71] = 0;
   out_8220635292339759608[72] = 0;
   out_8220635292339759608[73] = 0;
   out_8220635292339759608[74] = 0;
   out_8220635292339759608[75] = 0;
   out_8220635292339759608[76] = 1;
   out_8220635292339759608[77] = 0;
   out_8220635292339759608[78] = 0;
   out_8220635292339759608[79] = 0;
   out_8220635292339759608[80] = 0;
   out_8220635292339759608[81] = 0;
   out_8220635292339759608[82] = 0;
   out_8220635292339759608[83] = 0;
   out_8220635292339759608[84] = 0;
   out_8220635292339759608[85] = dt;
   out_8220635292339759608[86] = 0;
   out_8220635292339759608[87] = 0;
   out_8220635292339759608[88] = 0;
   out_8220635292339759608[89] = 0;
   out_8220635292339759608[90] = 0;
   out_8220635292339759608[91] = 0;
   out_8220635292339759608[92] = 0;
   out_8220635292339759608[93] = 0;
   out_8220635292339759608[94] = 0;
   out_8220635292339759608[95] = 1;
   out_8220635292339759608[96] = 0;
   out_8220635292339759608[97] = 0;
   out_8220635292339759608[98] = 0;
   out_8220635292339759608[99] = 0;
   out_8220635292339759608[100] = 0;
   out_8220635292339759608[101] = 0;
   out_8220635292339759608[102] = 0;
   out_8220635292339759608[103] = 0;
   out_8220635292339759608[104] = dt;
   out_8220635292339759608[105] = 0;
   out_8220635292339759608[106] = 0;
   out_8220635292339759608[107] = 0;
   out_8220635292339759608[108] = 0;
   out_8220635292339759608[109] = 0;
   out_8220635292339759608[110] = 0;
   out_8220635292339759608[111] = 0;
   out_8220635292339759608[112] = 0;
   out_8220635292339759608[113] = 0;
   out_8220635292339759608[114] = 1;
   out_8220635292339759608[115] = 0;
   out_8220635292339759608[116] = 0;
   out_8220635292339759608[117] = 0;
   out_8220635292339759608[118] = 0;
   out_8220635292339759608[119] = 0;
   out_8220635292339759608[120] = 0;
   out_8220635292339759608[121] = 0;
   out_8220635292339759608[122] = 0;
   out_8220635292339759608[123] = 0;
   out_8220635292339759608[124] = 0;
   out_8220635292339759608[125] = 0;
   out_8220635292339759608[126] = 0;
   out_8220635292339759608[127] = 0;
   out_8220635292339759608[128] = 0;
   out_8220635292339759608[129] = 0;
   out_8220635292339759608[130] = 0;
   out_8220635292339759608[131] = 0;
   out_8220635292339759608[132] = 0;
   out_8220635292339759608[133] = 1;
   out_8220635292339759608[134] = 0;
   out_8220635292339759608[135] = 0;
   out_8220635292339759608[136] = 0;
   out_8220635292339759608[137] = 0;
   out_8220635292339759608[138] = 0;
   out_8220635292339759608[139] = 0;
   out_8220635292339759608[140] = 0;
   out_8220635292339759608[141] = 0;
   out_8220635292339759608[142] = 0;
   out_8220635292339759608[143] = 0;
   out_8220635292339759608[144] = 0;
   out_8220635292339759608[145] = 0;
   out_8220635292339759608[146] = 0;
   out_8220635292339759608[147] = 0;
   out_8220635292339759608[148] = 0;
   out_8220635292339759608[149] = 0;
   out_8220635292339759608[150] = 0;
   out_8220635292339759608[151] = 0;
   out_8220635292339759608[152] = 1;
   out_8220635292339759608[153] = 0;
   out_8220635292339759608[154] = 0;
   out_8220635292339759608[155] = 0;
   out_8220635292339759608[156] = 0;
   out_8220635292339759608[157] = 0;
   out_8220635292339759608[158] = 0;
   out_8220635292339759608[159] = 0;
   out_8220635292339759608[160] = 0;
   out_8220635292339759608[161] = 0;
   out_8220635292339759608[162] = 0;
   out_8220635292339759608[163] = 0;
   out_8220635292339759608[164] = 0;
   out_8220635292339759608[165] = 0;
   out_8220635292339759608[166] = 0;
   out_8220635292339759608[167] = 0;
   out_8220635292339759608[168] = 0;
   out_8220635292339759608[169] = 0;
   out_8220635292339759608[170] = 0;
   out_8220635292339759608[171] = 1;
   out_8220635292339759608[172] = 0;
   out_8220635292339759608[173] = 0;
   out_8220635292339759608[174] = 0;
   out_8220635292339759608[175] = 0;
   out_8220635292339759608[176] = 0;
   out_8220635292339759608[177] = 0;
   out_8220635292339759608[178] = 0;
   out_8220635292339759608[179] = 0;
   out_8220635292339759608[180] = 0;
   out_8220635292339759608[181] = 0;
   out_8220635292339759608[182] = 0;
   out_8220635292339759608[183] = 0;
   out_8220635292339759608[184] = 0;
   out_8220635292339759608[185] = 0;
   out_8220635292339759608[186] = 0;
   out_8220635292339759608[187] = 0;
   out_8220635292339759608[188] = 0;
   out_8220635292339759608[189] = 0;
   out_8220635292339759608[190] = 1;
   out_8220635292339759608[191] = 0;
   out_8220635292339759608[192] = 0;
   out_8220635292339759608[193] = 0;
   out_8220635292339759608[194] = 0;
   out_8220635292339759608[195] = 0;
   out_8220635292339759608[196] = 0;
   out_8220635292339759608[197] = 0;
   out_8220635292339759608[198] = 0;
   out_8220635292339759608[199] = 0;
   out_8220635292339759608[200] = 0;
   out_8220635292339759608[201] = 0;
   out_8220635292339759608[202] = 0;
   out_8220635292339759608[203] = 0;
   out_8220635292339759608[204] = 0;
   out_8220635292339759608[205] = 0;
   out_8220635292339759608[206] = 0;
   out_8220635292339759608[207] = 0;
   out_8220635292339759608[208] = 0;
   out_8220635292339759608[209] = 1;
   out_8220635292339759608[210] = 0;
   out_8220635292339759608[211] = 0;
   out_8220635292339759608[212] = 0;
   out_8220635292339759608[213] = 0;
   out_8220635292339759608[214] = 0;
   out_8220635292339759608[215] = 0;
   out_8220635292339759608[216] = 0;
   out_8220635292339759608[217] = 0;
   out_8220635292339759608[218] = 0;
   out_8220635292339759608[219] = 0;
   out_8220635292339759608[220] = 0;
   out_8220635292339759608[221] = 0;
   out_8220635292339759608[222] = 0;
   out_8220635292339759608[223] = 0;
   out_8220635292339759608[224] = 0;
   out_8220635292339759608[225] = 0;
   out_8220635292339759608[226] = 0;
   out_8220635292339759608[227] = 0;
   out_8220635292339759608[228] = 1;
   out_8220635292339759608[229] = 0;
   out_8220635292339759608[230] = 0;
   out_8220635292339759608[231] = 0;
   out_8220635292339759608[232] = 0;
   out_8220635292339759608[233] = 0;
   out_8220635292339759608[234] = 0;
   out_8220635292339759608[235] = 0;
   out_8220635292339759608[236] = 0;
   out_8220635292339759608[237] = 0;
   out_8220635292339759608[238] = 0;
   out_8220635292339759608[239] = 0;
   out_8220635292339759608[240] = 0;
   out_8220635292339759608[241] = 0;
   out_8220635292339759608[242] = 0;
   out_8220635292339759608[243] = 0;
   out_8220635292339759608[244] = 0;
   out_8220635292339759608[245] = 0;
   out_8220635292339759608[246] = 0;
   out_8220635292339759608[247] = 1;
   out_8220635292339759608[248] = 0;
   out_8220635292339759608[249] = 0;
   out_8220635292339759608[250] = 0;
   out_8220635292339759608[251] = 0;
   out_8220635292339759608[252] = 0;
   out_8220635292339759608[253] = 0;
   out_8220635292339759608[254] = 0;
   out_8220635292339759608[255] = 0;
   out_8220635292339759608[256] = 0;
   out_8220635292339759608[257] = 0;
   out_8220635292339759608[258] = 0;
   out_8220635292339759608[259] = 0;
   out_8220635292339759608[260] = 0;
   out_8220635292339759608[261] = 0;
   out_8220635292339759608[262] = 0;
   out_8220635292339759608[263] = 0;
   out_8220635292339759608[264] = 0;
   out_8220635292339759608[265] = 0;
   out_8220635292339759608[266] = 1;
   out_8220635292339759608[267] = 0;
   out_8220635292339759608[268] = 0;
   out_8220635292339759608[269] = 0;
   out_8220635292339759608[270] = 0;
   out_8220635292339759608[271] = 0;
   out_8220635292339759608[272] = 0;
   out_8220635292339759608[273] = 0;
   out_8220635292339759608[274] = 0;
   out_8220635292339759608[275] = 0;
   out_8220635292339759608[276] = 0;
   out_8220635292339759608[277] = 0;
   out_8220635292339759608[278] = 0;
   out_8220635292339759608[279] = 0;
   out_8220635292339759608[280] = 0;
   out_8220635292339759608[281] = 0;
   out_8220635292339759608[282] = 0;
   out_8220635292339759608[283] = 0;
   out_8220635292339759608[284] = 0;
   out_8220635292339759608[285] = 1;
   out_8220635292339759608[286] = 0;
   out_8220635292339759608[287] = 0;
   out_8220635292339759608[288] = 0;
   out_8220635292339759608[289] = 0;
   out_8220635292339759608[290] = 0;
   out_8220635292339759608[291] = 0;
   out_8220635292339759608[292] = 0;
   out_8220635292339759608[293] = 0;
   out_8220635292339759608[294] = 0;
   out_8220635292339759608[295] = 0;
   out_8220635292339759608[296] = 0;
   out_8220635292339759608[297] = 0;
   out_8220635292339759608[298] = 0;
   out_8220635292339759608[299] = 0;
   out_8220635292339759608[300] = 0;
   out_8220635292339759608[301] = 0;
   out_8220635292339759608[302] = 0;
   out_8220635292339759608[303] = 0;
   out_8220635292339759608[304] = 1;
   out_8220635292339759608[305] = 0;
   out_8220635292339759608[306] = 0;
   out_8220635292339759608[307] = 0;
   out_8220635292339759608[308] = 0;
   out_8220635292339759608[309] = 0;
   out_8220635292339759608[310] = 0;
   out_8220635292339759608[311] = 0;
   out_8220635292339759608[312] = 0;
   out_8220635292339759608[313] = 0;
   out_8220635292339759608[314] = 0;
   out_8220635292339759608[315] = 0;
   out_8220635292339759608[316] = 0;
   out_8220635292339759608[317] = 0;
   out_8220635292339759608[318] = 0;
   out_8220635292339759608[319] = 0;
   out_8220635292339759608[320] = 0;
   out_8220635292339759608[321] = 0;
   out_8220635292339759608[322] = 0;
   out_8220635292339759608[323] = 1;
}
void h_4(double *state, double *unused, double *out_2097936204583725179) {
   out_2097936204583725179[0] = state[6] + state[9];
   out_2097936204583725179[1] = state[7] + state[10];
   out_2097936204583725179[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_4839409540176553033) {
   out_4839409540176553033[0] = 0;
   out_4839409540176553033[1] = 0;
   out_4839409540176553033[2] = 0;
   out_4839409540176553033[3] = 0;
   out_4839409540176553033[4] = 0;
   out_4839409540176553033[5] = 0;
   out_4839409540176553033[6] = 1;
   out_4839409540176553033[7] = 0;
   out_4839409540176553033[8] = 0;
   out_4839409540176553033[9] = 1;
   out_4839409540176553033[10] = 0;
   out_4839409540176553033[11] = 0;
   out_4839409540176553033[12] = 0;
   out_4839409540176553033[13] = 0;
   out_4839409540176553033[14] = 0;
   out_4839409540176553033[15] = 0;
   out_4839409540176553033[16] = 0;
   out_4839409540176553033[17] = 0;
   out_4839409540176553033[18] = 0;
   out_4839409540176553033[19] = 0;
   out_4839409540176553033[20] = 0;
   out_4839409540176553033[21] = 0;
   out_4839409540176553033[22] = 0;
   out_4839409540176553033[23] = 0;
   out_4839409540176553033[24] = 0;
   out_4839409540176553033[25] = 1;
   out_4839409540176553033[26] = 0;
   out_4839409540176553033[27] = 0;
   out_4839409540176553033[28] = 1;
   out_4839409540176553033[29] = 0;
   out_4839409540176553033[30] = 0;
   out_4839409540176553033[31] = 0;
   out_4839409540176553033[32] = 0;
   out_4839409540176553033[33] = 0;
   out_4839409540176553033[34] = 0;
   out_4839409540176553033[35] = 0;
   out_4839409540176553033[36] = 0;
   out_4839409540176553033[37] = 0;
   out_4839409540176553033[38] = 0;
   out_4839409540176553033[39] = 0;
   out_4839409540176553033[40] = 0;
   out_4839409540176553033[41] = 0;
   out_4839409540176553033[42] = 0;
   out_4839409540176553033[43] = 0;
   out_4839409540176553033[44] = 1;
   out_4839409540176553033[45] = 0;
   out_4839409540176553033[46] = 0;
   out_4839409540176553033[47] = 1;
   out_4839409540176553033[48] = 0;
   out_4839409540176553033[49] = 0;
   out_4839409540176553033[50] = 0;
   out_4839409540176553033[51] = 0;
   out_4839409540176553033[52] = 0;
   out_4839409540176553033[53] = 0;
}
void h_10(double *state, double *unused, double *out_29444642201375045) {
   out_29444642201375045[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_29444642201375045[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_29444642201375045[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_1070049335288984001) {
   out_1070049335288984001[0] = 0;
   out_1070049335288984001[1] = 9.8100000000000005*cos(state[1]);
   out_1070049335288984001[2] = 0;
   out_1070049335288984001[3] = 0;
   out_1070049335288984001[4] = -state[8];
   out_1070049335288984001[5] = state[7];
   out_1070049335288984001[6] = 0;
   out_1070049335288984001[7] = state[5];
   out_1070049335288984001[8] = -state[4];
   out_1070049335288984001[9] = 0;
   out_1070049335288984001[10] = 0;
   out_1070049335288984001[11] = 0;
   out_1070049335288984001[12] = 1;
   out_1070049335288984001[13] = 0;
   out_1070049335288984001[14] = 0;
   out_1070049335288984001[15] = 1;
   out_1070049335288984001[16] = 0;
   out_1070049335288984001[17] = 0;
   out_1070049335288984001[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_1070049335288984001[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_1070049335288984001[20] = 0;
   out_1070049335288984001[21] = state[8];
   out_1070049335288984001[22] = 0;
   out_1070049335288984001[23] = -state[6];
   out_1070049335288984001[24] = -state[5];
   out_1070049335288984001[25] = 0;
   out_1070049335288984001[26] = state[3];
   out_1070049335288984001[27] = 0;
   out_1070049335288984001[28] = 0;
   out_1070049335288984001[29] = 0;
   out_1070049335288984001[30] = 0;
   out_1070049335288984001[31] = 1;
   out_1070049335288984001[32] = 0;
   out_1070049335288984001[33] = 0;
   out_1070049335288984001[34] = 1;
   out_1070049335288984001[35] = 0;
   out_1070049335288984001[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_1070049335288984001[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_1070049335288984001[38] = 0;
   out_1070049335288984001[39] = -state[7];
   out_1070049335288984001[40] = state[6];
   out_1070049335288984001[41] = 0;
   out_1070049335288984001[42] = state[4];
   out_1070049335288984001[43] = -state[3];
   out_1070049335288984001[44] = 0;
   out_1070049335288984001[45] = 0;
   out_1070049335288984001[46] = 0;
   out_1070049335288984001[47] = 0;
   out_1070049335288984001[48] = 0;
   out_1070049335288984001[49] = 0;
   out_1070049335288984001[50] = 1;
   out_1070049335288984001[51] = 0;
   out_1070049335288984001[52] = 0;
   out_1070049335288984001[53] = 1;
}
void h_13(double *state, double *unused, double *out_61045813616994293) {
   out_61045813616994293[0] = state[3];
   out_61045813616994293[1] = state[4];
   out_61045813616994293[2] = state[5];
}
void H_13(double *state, double *unused, double *out_8051683365508885834) {
   out_8051683365508885834[0] = 0;
   out_8051683365508885834[1] = 0;
   out_8051683365508885834[2] = 0;
   out_8051683365508885834[3] = 1;
   out_8051683365508885834[4] = 0;
   out_8051683365508885834[5] = 0;
   out_8051683365508885834[6] = 0;
   out_8051683365508885834[7] = 0;
   out_8051683365508885834[8] = 0;
   out_8051683365508885834[9] = 0;
   out_8051683365508885834[10] = 0;
   out_8051683365508885834[11] = 0;
   out_8051683365508885834[12] = 0;
   out_8051683365508885834[13] = 0;
   out_8051683365508885834[14] = 0;
   out_8051683365508885834[15] = 0;
   out_8051683365508885834[16] = 0;
   out_8051683365508885834[17] = 0;
   out_8051683365508885834[18] = 0;
   out_8051683365508885834[19] = 0;
   out_8051683365508885834[20] = 0;
   out_8051683365508885834[21] = 0;
   out_8051683365508885834[22] = 1;
   out_8051683365508885834[23] = 0;
   out_8051683365508885834[24] = 0;
   out_8051683365508885834[25] = 0;
   out_8051683365508885834[26] = 0;
   out_8051683365508885834[27] = 0;
   out_8051683365508885834[28] = 0;
   out_8051683365508885834[29] = 0;
   out_8051683365508885834[30] = 0;
   out_8051683365508885834[31] = 0;
   out_8051683365508885834[32] = 0;
   out_8051683365508885834[33] = 0;
   out_8051683365508885834[34] = 0;
   out_8051683365508885834[35] = 0;
   out_8051683365508885834[36] = 0;
   out_8051683365508885834[37] = 0;
   out_8051683365508885834[38] = 0;
   out_8051683365508885834[39] = 0;
   out_8051683365508885834[40] = 0;
   out_8051683365508885834[41] = 1;
   out_8051683365508885834[42] = 0;
   out_8051683365508885834[43] = 0;
   out_8051683365508885834[44] = 0;
   out_8051683365508885834[45] = 0;
   out_8051683365508885834[46] = 0;
   out_8051683365508885834[47] = 0;
   out_8051683365508885834[48] = 0;
   out_8051683365508885834[49] = 0;
   out_8051683365508885834[50] = 0;
   out_8051683365508885834[51] = 0;
   out_8051683365508885834[52] = 0;
   out_8051683365508885834[53] = 0;
}
void h_14(double *state, double *unused, double *out_8545162578881105562) {
   out_8545162578881105562[0] = state[6];
   out_8545162578881105562[1] = state[7];
   out_8545162578881105562[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4404293013531669434) {
   out_4404293013531669434[0] = 0;
   out_4404293013531669434[1] = 0;
   out_4404293013531669434[2] = 0;
   out_4404293013531669434[3] = 0;
   out_4404293013531669434[4] = 0;
   out_4404293013531669434[5] = 0;
   out_4404293013531669434[6] = 1;
   out_4404293013531669434[7] = 0;
   out_4404293013531669434[8] = 0;
   out_4404293013531669434[9] = 0;
   out_4404293013531669434[10] = 0;
   out_4404293013531669434[11] = 0;
   out_4404293013531669434[12] = 0;
   out_4404293013531669434[13] = 0;
   out_4404293013531669434[14] = 0;
   out_4404293013531669434[15] = 0;
   out_4404293013531669434[16] = 0;
   out_4404293013531669434[17] = 0;
   out_4404293013531669434[18] = 0;
   out_4404293013531669434[19] = 0;
   out_4404293013531669434[20] = 0;
   out_4404293013531669434[21] = 0;
   out_4404293013531669434[22] = 0;
   out_4404293013531669434[23] = 0;
   out_4404293013531669434[24] = 0;
   out_4404293013531669434[25] = 1;
   out_4404293013531669434[26] = 0;
   out_4404293013531669434[27] = 0;
   out_4404293013531669434[28] = 0;
   out_4404293013531669434[29] = 0;
   out_4404293013531669434[30] = 0;
   out_4404293013531669434[31] = 0;
   out_4404293013531669434[32] = 0;
   out_4404293013531669434[33] = 0;
   out_4404293013531669434[34] = 0;
   out_4404293013531669434[35] = 0;
   out_4404293013531669434[36] = 0;
   out_4404293013531669434[37] = 0;
   out_4404293013531669434[38] = 0;
   out_4404293013531669434[39] = 0;
   out_4404293013531669434[40] = 0;
   out_4404293013531669434[41] = 0;
   out_4404293013531669434[42] = 0;
   out_4404293013531669434[43] = 0;
   out_4404293013531669434[44] = 1;
   out_4404293013531669434[45] = 0;
   out_4404293013531669434[46] = 0;
   out_4404293013531669434[47] = 0;
   out_4404293013531669434[48] = 0;
   out_4404293013531669434[49] = 0;
   out_4404293013531669434[50] = 0;
   out_4404293013531669434[51] = 0;
   out_4404293013531669434[52] = 0;
   out_4404293013531669434[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3597460724364137401) {
  err_fun(nom_x, delta_x, out_3597460724364137401);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1062002485999931142) {
  inv_err_fun(nom_x, true_x, out_1062002485999931142);
}
void pose_H_mod_fun(double *state, double *out_4662972867475177241) {
  H_mod_fun(state, out_4662972867475177241);
}
void pose_f_fun(double *state, double dt, double *out_3840229658681249647) {
  f_fun(state,  dt, out_3840229658681249647);
}
void pose_F_fun(double *state, double dt, double *out_8220635292339759608) {
  F_fun(state,  dt, out_8220635292339759608);
}
void pose_h_4(double *state, double *unused, double *out_2097936204583725179) {
  h_4(state, unused, out_2097936204583725179);
}
void pose_H_4(double *state, double *unused, double *out_4839409540176553033) {
  H_4(state, unused, out_4839409540176553033);
}
void pose_h_10(double *state, double *unused, double *out_29444642201375045) {
  h_10(state, unused, out_29444642201375045);
}
void pose_H_10(double *state, double *unused, double *out_1070049335288984001) {
  H_10(state, unused, out_1070049335288984001);
}
void pose_h_13(double *state, double *unused, double *out_61045813616994293) {
  h_13(state, unused, out_61045813616994293);
}
void pose_H_13(double *state, double *unused, double *out_8051683365508885834) {
  H_13(state, unused, out_8051683365508885834);
}
void pose_h_14(double *state, double *unused, double *out_8545162578881105562) {
  h_14(state, unused, out_8545162578881105562);
}
void pose_H_14(double *state, double *unused, double *out_4404293013531669434) {
  H_14(state, unused, out_4404293013531669434);
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
