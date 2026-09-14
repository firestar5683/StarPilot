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
void err_fun(double *nom_x, double *delta_x, double *out_8427200704796300077) {
   out_8427200704796300077[0] = delta_x[0] + nom_x[0];
   out_8427200704796300077[1] = delta_x[1] + nom_x[1];
   out_8427200704796300077[2] = delta_x[2] + nom_x[2];
   out_8427200704796300077[3] = delta_x[3] + nom_x[3];
   out_8427200704796300077[4] = delta_x[4] + nom_x[4];
   out_8427200704796300077[5] = delta_x[5] + nom_x[5];
   out_8427200704796300077[6] = delta_x[6] + nom_x[6];
   out_8427200704796300077[7] = delta_x[7] + nom_x[7];
   out_8427200704796300077[8] = delta_x[8] + nom_x[8];
   out_8427200704796300077[9] = delta_x[9] + nom_x[9];
   out_8427200704796300077[10] = delta_x[10] + nom_x[10];
   out_8427200704796300077[11] = delta_x[11] + nom_x[11];
   out_8427200704796300077[12] = delta_x[12] + nom_x[12];
   out_8427200704796300077[13] = delta_x[13] + nom_x[13];
   out_8427200704796300077[14] = delta_x[14] + nom_x[14];
   out_8427200704796300077[15] = delta_x[15] + nom_x[15];
   out_8427200704796300077[16] = delta_x[16] + nom_x[16];
   out_8427200704796300077[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_209888032840788679) {
   out_209888032840788679[0] = -nom_x[0] + true_x[0];
   out_209888032840788679[1] = -nom_x[1] + true_x[1];
   out_209888032840788679[2] = -nom_x[2] + true_x[2];
   out_209888032840788679[3] = -nom_x[3] + true_x[3];
   out_209888032840788679[4] = -nom_x[4] + true_x[4];
   out_209888032840788679[5] = -nom_x[5] + true_x[5];
   out_209888032840788679[6] = -nom_x[6] + true_x[6];
   out_209888032840788679[7] = -nom_x[7] + true_x[7];
   out_209888032840788679[8] = -nom_x[8] + true_x[8];
   out_209888032840788679[9] = -nom_x[9] + true_x[9];
   out_209888032840788679[10] = -nom_x[10] + true_x[10];
   out_209888032840788679[11] = -nom_x[11] + true_x[11];
   out_209888032840788679[12] = -nom_x[12] + true_x[12];
   out_209888032840788679[13] = -nom_x[13] + true_x[13];
   out_209888032840788679[14] = -nom_x[14] + true_x[14];
   out_209888032840788679[15] = -nom_x[15] + true_x[15];
   out_209888032840788679[16] = -nom_x[16] + true_x[16];
   out_209888032840788679[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5010822586708507522) {
   out_5010822586708507522[0] = 1.0;
   out_5010822586708507522[1] = 0.0;
   out_5010822586708507522[2] = 0.0;
   out_5010822586708507522[3] = 0.0;
   out_5010822586708507522[4] = 0.0;
   out_5010822586708507522[5] = 0.0;
   out_5010822586708507522[6] = 0.0;
   out_5010822586708507522[7] = 0.0;
   out_5010822586708507522[8] = 0.0;
   out_5010822586708507522[9] = 0.0;
   out_5010822586708507522[10] = 0.0;
   out_5010822586708507522[11] = 0.0;
   out_5010822586708507522[12] = 0.0;
   out_5010822586708507522[13] = 0.0;
   out_5010822586708507522[14] = 0.0;
   out_5010822586708507522[15] = 0.0;
   out_5010822586708507522[16] = 0.0;
   out_5010822586708507522[17] = 0.0;
   out_5010822586708507522[18] = 0.0;
   out_5010822586708507522[19] = 1.0;
   out_5010822586708507522[20] = 0.0;
   out_5010822586708507522[21] = 0.0;
   out_5010822586708507522[22] = 0.0;
   out_5010822586708507522[23] = 0.0;
   out_5010822586708507522[24] = 0.0;
   out_5010822586708507522[25] = 0.0;
   out_5010822586708507522[26] = 0.0;
   out_5010822586708507522[27] = 0.0;
   out_5010822586708507522[28] = 0.0;
   out_5010822586708507522[29] = 0.0;
   out_5010822586708507522[30] = 0.0;
   out_5010822586708507522[31] = 0.0;
   out_5010822586708507522[32] = 0.0;
   out_5010822586708507522[33] = 0.0;
   out_5010822586708507522[34] = 0.0;
   out_5010822586708507522[35] = 0.0;
   out_5010822586708507522[36] = 0.0;
   out_5010822586708507522[37] = 0.0;
   out_5010822586708507522[38] = 1.0;
   out_5010822586708507522[39] = 0.0;
   out_5010822586708507522[40] = 0.0;
   out_5010822586708507522[41] = 0.0;
   out_5010822586708507522[42] = 0.0;
   out_5010822586708507522[43] = 0.0;
   out_5010822586708507522[44] = 0.0;
   out_5010822586708507522[45] = 0.0;
   out_5010822586708507522[46] = 0.0;
   out_5010822586708507522[47] = 0.0;
   out_5010822586708507522[48] = 0.0;
   out_5010822586708507522[49] = 0.0;
   out_5010822586708507522[50] = 0.0;
   out_5010822586708507522[51] = 0.0;
   out_5010822586708507522[52] = 0.0;
   out_5010822586708507522[53] = 0.0;
   out_5010822586708507522[54] = 0.0;
   out_5010822586708507522[55] = 0.0;
   out_5010822586708507522[56] = 0.0;
   out_5010822586708507522[57] = 1.0;
   out_5010822586708507522[58] = 0.0;
   out_5010822586708507522[59] = 0.0;
   out_5010822586708507522[60] = 0.0;
   out_5010822586708507522[61] = 0.0;
   out_5010822586708507522[62] = 0.0;
   out_5010822586708507522[63] = 0.0;
   out_5010822586708507522[64] = 0.0;
   out_5010822586708507522[65] = 0.0;
   out_5010822586708507522[66] = 0.0;
   out_5010822586708507522[67] = 0.0;
   out_5010822586708507522[68] = 0.0;
   out_5010822586708507522[69] = 0.0;
   out_5010822586708507522[70] = 0.0;
   out_5010822586708507522[71] = 0.0;
   out_5010822586708507522[72] = 0.0;
   out_5010822586708507522[73] = 0.0;
   out_5010822586708507522[74] = 0.0;
   out_5010822586708507522[75] = 0.0;
   out_5010822586708507522[76] = 1.0;
   out_5010822586708507522[77] = 0.0;
   out_5010822586708507522[78] = 0.0;
   out_5010822586708507522[79] = 0.0;
   out_5010822586708507522[80] = 0.0;
   out_5010822586708507522[81] = 0.0;
   out_5010822586708507522[82] = 0.0;
   out_5010822586708507522[83] = 0.0;
   out_5010822586708507522[84] = 0.0;
   out_5010822586708507522[85] = 0.0;
   out_5010822586708507522[86] = 0.0;
   out_5010822586708507522[87] = 0.0;
   out_5010822586708507522[88] = 0.0;
   out_5010822586708507522[89] = 0.0;
   out_5010822586708507522[90] = 0.0;
   out_5010822586708507522[91] = 0.0;
   out_5010822586708507522[92] = 0.0;
   out_5010822586708507522[93] = 0.0;
   out_5010822586708507522[94] = 0.0;
   out_5010822586708507522[95] = 1.0;
   out_5010822586708507522[96] = 0.0;
   out_5010822586708507522[97] = 0.0;
   out_5010822586708507522[98] = 0.0;
   out_5010822586708507522[99] = 0.0;
   out_5010822586708507522[100] = 0.0;
   out_5010822586708507522[101] = 0.0;
   out_5010822586708507522[102] = 0.0;
   out_5010822586708507522[103] = 0.0;
   out_5010822586708507522[104] = 0.0;
   out_5010822586708507522[105] = 0.0;
   out_5010822586708507522[106] = 0.0;
   out_5010822586708507522[107] = 0.0;
   out_5010822586708507522[108] = 0.0;
   out_5010822586708507522[109] = 0.0;
   out_5010822586708507522[110] = 0.0;
   out_5010822586708507522[111] = 0.0;
   out_5010822586708507522[112] = 0.0;
   out_5010822586708507522[113] = 0.0;
   out_5010822586708507522[114] = 1.0;
   out_5010822586708507522[115] = 0.0;
   out_5010822586708507522[116] = 0.0;
   out_5010822586708507522[117] = 0.0;
   out_5010822586708507522[118] = 0.0;
   out_5010822586708507522[119] = 0.0;
   out_5010822586708507522[120] = 0.0;
   out_5010822586708507522[121] = 0.0;
   out_5010822586708507522[122] = 0.0;
   out_5010822586708507522[123] = 0.0;
   out_5010822586708507522[124] = 0.0;
   out_5010822586708507522[125] = 0.0;
   out_5010822586708507522[126] = 0.0;
   out_5010822586708507522[127] = 0.0;
   out_5010822586708507522[128] = 0.0;
   out_5010822586708507522[129] = 0.0;
   out_5010822586708507522[130] = 0.0;
   out_5010822586708507522[131] = 0.0;
   out_5010822586708507522[132] = 0.0;
   out_5010822586708507522[133] = 1.0;
   out_5010822586708507522[134] = 0.0;
   out_5010822586708507522[135] = 0.0;
   out_5010822586708507522[136] = 0.0;
   out_5010822586708507522[137] = 0.0;
   out_5010822586708507522[138] = 0.0;
   out_5010822586708507522[139] = 0.0;
   out_5010822586708507522[140] = 0.0;
   out_5010822586708507522[141] = 0.0;
   out_5010822586708507522[142] = 0.0;
   out_5010822586708507522[143] = 0.0;
   out_5010822586708507522[144] = 0.0;
   out_5010822586708507522[145] = 0.0;
   out_5010822586708507522[146] = 0.0;
   out_5010822586708507522[147] = 0.0;
   out_5010822586708507522[148] = 0.0;
   out_5010822586708507522[149] = 0.0;
   out_5010822586708507522[150] = 0.0;
   out_5010822586708507522[151] = 0.0;
   out_5010822586708507522[152] = 1.0;
   out_5010822586708507522[153] = 0.0;
   out_5010822586708507522[154] = 0.0;
   out_5010822586708507522[155] = 0.0;
   out_5010822586708507522[156] = 0.0;
   out_5010822586708507522[157] = 0.0;
   out_5010822586708507522[158] = 0.0;
   out_5010822586708507522[159] = 0.0;
   out_5010822586708507522[160] = 0.0;
   out_5010822586708507522[161] = 0.0;
   out_5010822586708507522[162] = 0.0;
   out_5010822586708507522[163] = 0.0;
   out_5010822586708507522[164] = 0.0;
   out_5010822586708507522[165] = 0.0;
   out_5010822586708507522[166] = 0.0;
   out_5010822586708507522[167] = 0.0;
   out_5010822586708507522[168] = 0.0;
   out_5010822586708507522[169] = 0.0;
   out_5010822586708507522[170] = 0.0;
   out_5010822586708507522[171] = 1.0;
   out_5010822586708507522[172] = 0.0;
   out_5010822586708507522[173] = 0.0;
   out_5010822586708507522[174] = 0.0;
   out_5010822586708507522[175] = 0.0;
   out_5010822586708507522[176] = 0.0;
   out_5010822586708507522[177] = 0.0;
   out_5010822586708507522[178] = 0.0;
   out_5010822586708507522[179] = 0.0;
   out_5010822586708507522[180] = 0.0;
   out_5010822586708507522[181] = 0.0;
   out_5010822586708507522[182] = 0.0;
   out_5010822586708507522[183] = 0.0;
   out_5010822586708507522[184] = 0.0;
   out_5010822586708507522[185] = 0.0;
   out_5010822586708507522[186] = 0.0;
   out_5010822586708507522[187] = 0.0;
   out_5010822586708507522[188] = 0.0;
   out_5010822586708507522[189] = 0.0;
   out_5010822586708507522[190] = 1.0;
   out_5010822586708507522[191] = 0.0;
   out_5010822586708507522[192] = 0.0;
   out_5010822586708507522[193] = 0.0;
   out_5010822586708507522[194] = 0.0;
   out_5010822586708507522[195] = 0.0;
   out_5010822586708507522[196] = 0.0;
   out_5010822586708507522[197] = 0.0;
   out_5010822586708507522[198] = 0.0;
   out_5010822586708507522[199] = 0.0;
   out_5010822586708507522[200] = 0.0;
   out_5010822586708507522[201] = 0.0;
   out_5010822586708507522[202] = 0.0;
   out_5010822586708507522[203] = 0.0;
   out_5010822586708507522[204] = 0.0;
   out_5010822586708507522[205] = 0.0;
   out_5010822586708507522[206] = 0.0;
   out_5010822586708507522[207] = 0.0;
   out_5010822586708507522[208] = 0.0;
   out_5010822586708507522[209] = 1.0;
   out_5010822586708507522[210] = 0.0;
   out_5010822586708507522[211] = 0.0;
   out_5010822586708507522[212] = 0.0;
   out_5010822586708507522[213] = 0.0;
   out_5010822586708507522[214] = 0.0;
   out_5010822586708507522[215] = 0.0;
   out_5010822586708507522[216] = 0.0;
   out_5010822586708507522[217] = 0.0;
   out_5010822586708507522[218] = 0.0;
   out_5010822586708507522[219] = 0.0;
   out_5010822586708507522[220] = 0.0;
   out_5010822586708507522[221] = 0.0;
   out_5010822586708507522[222] = 0.0;
   out_5010822586708507522[223] = 0.0;
   out_5010822586708507522[224] = 0.0;
   out_5010822586708507522[225] = 0.0;
   out_5010822586708507522[226] = 0.0;
   out_5010822586708507522[227] = 0.0;
   out_5010822586708507522[228] = 1.0;
   out_5010822586708507522[229] = 0.0;
   out_5010822586708507522[230] = 0.0;
   out_5010822586708507522[231] = 0.0;
   out_5010822586708507522[232] = 0.0;
   out_5010822586708507522[233] = 0.0;
   out_5010822586708507522[234] = 0.0;
   out_5010822586708507522[235] = 0.0;
   out_5010822586708507522[236] = 0.0;
   out_5010822586708507522[237] = 0.0;
   out_5010822586708507522[238] = 0.0;
   out_5010822586708507522[239] = 0.0;
   out_5010822586708507522[240] = 0.0;
   out_5010822586708507522[241] = 0.0;
   out_5010822586708507522[242] = 0.0;
   out_5010822586708507522[243] = 0.0;
   out_5010822586708507522[244] = 0.0;
   out_5010822586708507522[245] = 0.0;
   out_5010822586708507522[246] = 0.0;
   out_5010822586708507522[247] = 1.0;
   out_5010822586708507522[248] = 0.0;
   out_5010822586708507522[249] = 0.0;
   out_5010822586708507522[250] = 0.0;
   out_5010822586708507522[251] = 0.0;
   out_5010822586708507522[252] = 0.0;
   out_5010822586708507522[253] = 0.0;
   out_5010822586708507522[254] = 0.0;
   out_5010822586708507522[255] = 0.0;
   out_5010822586708507522[256] = 0.0;
   out_5010822586708507522[257] = 0.0;
   out_5010822586708507522[258] = 0.0;
   out_5010822586708507522[259] = 0.0;
   out_5010822586708507522[260] = 0.0;
   out_5010822586708507522[261] = 0.0;
   out_5010822586708507522[262] = 0.0;
   out_5010822586708507522[263] = 0.0;
   out_5010822586708507522[264] = 0.0;
   out_5010822586708507522[265] = 0.0;
   out_5010822586708507522[266] = 1.0;
   out_5010822586708507522[267] = 0.0;
   out_5010822586708507522[268] = 0.0;
   out_5010822586708507522[269] = 0.0;
   out_5010822586708507522[270] = 0.0;
   out_5010822586708507522[271] = 0.0;
   out_5010822586708507522[272] = 0.0;
   out_5010822586708507522[273] = 0.0;
   out_5010822586708507522[274] = 0.0;
   out_5010822586708507522[275] = 0.0;
   out_5010822586708507522[276] = 0.0;
   out_5010822586708507522[277] = 0.0;
   out_5010822586708507522[278] = 0.0;
   out_5010822586708507522[279] = 0.0;
   out_5010822586708507522[280] = 0.0;
   out_5010822586708507522[281] = 0.0;
   out_5010822586708507522[282] = 0.0;
   out_5010822586708507522[283] = 0.0;
   out_5010822586708507522[284] = 0.0;
   out_5010822586708507522[285] = 1.0;
   out_5010822586708507522[286] = 0.0;
   out_5010822586708507522[287] = 0.0;
   out_5010822586708507522[288] = 0.0;
   out_5010822586708507522[289] = 0.0;
   out_5010822586708507522[290] = 0.0;
   out_5010822586708507522[291] = 0.0;
   out_5010822586708507522[292] = 0.0;
   out_5010822586708507522[293] = 0.0;
   out_5010822586708507522[294] = 0.0;
   out_5010822586708507522[295] = 0.0;
   out_5010822586708507522[296] = 0.0;
   out_5010822586708507522[297] = 0.0;
   out_5010822586708507522[298] = 0.0;
   out_5010822586708507522[299] = 0.0;
   out_5010822586708507522[300] = 0.0;
   out_5010822586708507522[301] = 0.0;
   out_5010822586708507522[302] = 0.0;
   out_5010822586708507522[303] = 0.0;
   out_5010822586708507522[304] = 1.0;
   out_5010822586708507522[305] = 0.0;
   out_5010822586708507522[306] = 0.0;
   out_5010822586708507522[307] = 0.0;
   out_5010822586708507522[308] = 0.0;
   out_5010822586708507522[309] = 0.0;
   out_5010822586708507522[310] = 0.0;
   out_5010822586708507522[311] = 0.0;
   out_5010822586708507522[312] = 0.0;
   out_5010822586708507522[313] = 0.0;
   out_5010822586708507522[314] = 0.0;
   out_5010822586708507522[315] = 0.0;
   out_5010822586708507522[316] = 0.0;
   out_5010822586708507522[317] = 0.0;
   out_5010822586708507522[318] = 0.0;
   out_5010822586708507522[319] = 0.0;
   out_5010822586708507522[320] = 0.0;
   out_5010822586708507522[321] = 0.0;
   out_5010822586708507522[322] = 0.0;
   out_5010822586708507522[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8028362113385460735) {
   out_8028362113385460735[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8028362113385460735[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8028362113385460735[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8028362113385460735[3] = dt*state[12] + state[3];
   out_8028362113385460735[4] = dt*state[13] + state[4];
   out_8028362113385460735[5] = dt*state[14] + state[5];
   out_8028362113385460735[6] = state[6];
   out_8028362113385460735[7] = state[7];
   out_8028362113385460735[8] = state[8];
   out_8028362113385460735[9] = state[9];
   out_8028362113385460735[10] = state[10];
   out_8028362113385460735[11] = state[11];
   out_8028362113385460735[12] = state[12];
   out_8028362113385460735[13] = state[13];
   out_8028362113385460735[14] = state[14];
   out_8028362113385460735[15] = state[15];
   out_8028362113385460735[16] = state[16];
   out_8028362113385460735[17] = state[17];
}
void F_fun(double *state, double dt, double *out_435032814721793170) {
   out_435032814721793170[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435032814721793170[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435032814721793170[2] = 0;
   out_435032814721793170[3] = 0;
   out_435032814721793170[4] = 0;
   out_435032814721793170[5] = 0;
   out_435032814721793170[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435032814721793170[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435032814721793170[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435032814721793170[9] = 0;
   out_435032814721793170[10] = 0;
   out_435032814721793170[11] = 0;
   out_435032814721793170[12] = 0;
   out_435032814721793170[13] = 0;
   out_435032814721793170[14] = 0;
   out_435032814721793170[15] = 0;
   out_435032814721793170[16] = 0;
   out_435032814721793170[17] = 0;
   out_435032814721793170[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435032814721793170[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435032814721793170[20] = 0;
   out_435032814721793170[21] = 0;
   out_435032814721793170[22] = 0;
   out_435032814721793170[23] = 0;
   out_435032814721793170[24] = 0;
   out_435032814721793170[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435032814721793170[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435032814721793170[27] = 0;
   out_435032814721793170[28] = 0;
   out_435032814721793170[29] = 0;
   out_435032814721793170[30] = 0;
   out_435032814721793170[31] = 0;
   out_435032814721793170[32] = 0;
   out_435032814721793170[33] = 0;
   out_435032814721793170[34] = 0;
   out_435032814721793170[35] = 0;
   out_435032814721793170[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435032814721793170[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435032814721793170[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435032814721793170[39] = 0;
   out_435032814721793170[40] = 0;
   out_435032814721793170[41] = 0;
   out_435032814721793170[42] = 0;
   out_435032814721793170[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435032814721793170[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435032814721793170[45] = 0;
   out_435032814721793170[46] = 0;
   out_435032814721793170[47] = 0;
   out_435032814721793170[48] = 0;
   out_435032814721793170[49] = 0;
   out_435032814721793170[50] = 0;
   out_435032814721793170[51] = 0;
   out_435032814721793170[52] = 0;
   out_435032814721793170[53] = 0;
   out_435032814721793170[54] = 0;
   out_435032814721793170[55] = 0;
   out_435032814721793170[56] = 0;
   out_435032814721793170[57] = 1;
   out_435032814721793170[58] = 0;
   out_435032814721793170[59] = 0;
   out_435032814721793170[60] = 0;
   out_435032814721793170[61] = 0;
   out_435032814721793170[62] = 0;
   out_435032814721793170[63] = 0;
   out_435032814721793170[64] = 0;
   out_435032814721793170[65] = 0;
   out_435032814721793170[66] = dt;
   out_435032814721793170[67] = 0;
   out_435032814721793170[68] = 0;
   out_435032814721793170[69] = 0;
   out_435032814721793170[70] = 0;
   out_435032814721793170[71] = 0;
   out_435032814721793170[72] = 0;
   out_435032814721793170[73] = 0;
   out_435032814721793170[74] = 0;
   out_435032814721793170[75] = 0;
   out_435032814721793170[76] = 1;
   out_435032814721793170[77] = 0;
   out_435032814721793170[78] = 0;
   out_435032814721793170[79] = 0;
   out_435032814721793170[80] = 0;
   out_435032814721793170[81] = 0;
   out_435032814721793170[82] = 0;
   out_435032814721793170[83] = 0;
   out_435032814721793170[84] = 0;
   out_435032814721793170[85] = dt;
   out_435032814721793170[86] = 0;
   out_435032814721793170[87] = 0;
   out_435032814721793170[88] = 0;
   out_435032814721793170[89] = 0;
   out_435032814721793170[90] = 0;
   out_435032814721793170[91] = 0;
   out_435032814721793170[92] = 0;
   out_435032814721793170[93] = 0;
   out_435032814721793170[94] = 0;
   out_435032814721793170[95] = 1;
   out_435032814721793170[96] = 0;
   out_435032814721793170[97] = 0;
   out_435032814721793170[98] = 0;
   out_435032814721793170[99] = 0;
   out_435032814721793170[100] = 0;
   out_435032814721793170[101] = 0;
   out_435032814721793170[102] = 0;
   out_435032814721793170[103] = 0;
   out_435032814721793170[104] = dt;
   out_435032814721793170[105] = 0;
   out_435032814721793170[106] = 0;
   out_435032814721793170[107] = 0;
   out_435032814721793170[108] = 0;
   out_435032814721793170[109] = 0;
   out_435032814721793170[110] = 0;
   out_435032814721793170[111] = 0;
   out_435032814721793170[112] = 0;
   out_435032814721793170[113] = 0;
   out_435032814721793170[114] = 1;
   out_435032814721793170[115] = 0;
   out_435032814721793170[116] = 0;
   out_435032814721793170[117] = 0;
   out_435032814721793170[118] = 0;
   out_435032814721793170[119] = 0;
   out_435032814721793170[120] = 0;
   out_435032814721793170[121] = 0;
   out_435032814721793170[122] = 0;
   out_435032814721793170[123] = 0;
   out_435032814721793170[124] = 0;
   out_435032814721793170[125] = 0;
   out_435032814721793170[126] = 0;
   out_435032814721793170[127] = 0;
   out_435032814721793170[128] = 0;
   out_435032814721793170[129] = 0;
   out_435032814721793170[130] = 0;
   out_435032814721793170[131] = 0;
   out_435032814721793170[132] = 0;
   out_435032814721793170[133] = 1;
   out_435032814721793170[134] = 0;
   out_435032814721793170[135] = 0;
   out_435032814721793170[136] = 0;
   out_435032814721793170[137] = 0;
   out_435032814721793170[138] = 0;
   out_435032814721793170[139] = 0;
   out_435032814721793170[140] = 0;
   out_435032814721793170[141] = 0;
   out_435032814721793170[142] = 0;
   out_435032814721793170[143] = 0;
   out_435032814721793170[144] = 0;
   out_435032814721793170[145] = 0;
   out_435032814721793170[146] = 0;
   out_435032814721793170[147] = 0;
   out_435032814721793170[148] = 0;
   out_435032814721793170[149] = 0;
   out_435032814721793170[150] = 0;
   out_435032814721793170[151] = 0;
   out_435032814721793170[152] = 1;
   out_435032814721793170[153] = 0;
   out_435032814721793170[154] = 0;
   out_435032814721793170[155] = 0;
   out_435032814721793170[156] = 0;
   out_435032814721793170[157] = 0;
   out_435032814721793170[158] = 0;
   out_435032814721793170[159] = 0;
   out_435032814721793170[160] = 0;
   out_435032814721793170[161] = 0;
   out_435032814721793170[162] = 0;
   out_435032814721793170[163] = 0;
   out_435032814721793170[164] = 0;
   out_435032814721793170[165] = 0;
   out_435032814721793170[166] = 0;
   out_435032814721793170[167] = 0;
   out_435032814721793170[168] = 0;
   out_435032814721793170[169] = 0;
   out_435032814721793170[170] = 0;
   out_435032814721793170[171] = 1;
   out_435032814721793170[172] = 0;
   out_435032814721793170[173] = 0;
   out_435032814721793170[174] = 0;
   out_435032814721793170[175] = 0;
   out_435032814721793170[176] = 0;
   out_435032814721793170[177] = 0;
   out_435032814721793170[178] = 0;
   out_435032814721793170[179] = 0;
   out_435032814721793170[180] = 0;
   out_435032814721793170[181] = 0;
   out_435032814721793170[182] = 0;
   out_435032814721793170[183] = 0;
   out_435032814721793170[184] = 0;
   out_435032814721793170[185] = 0;
   out_435032814721793170[186] = 0;
   out_435032814721793170[187] = 0;
   out_435032814721793170[188] = 0;
   out_435032814721793170[189] = 0;
   out_435032814721793170[190] = 1;
   out_435032814721793170[191] = 0;
   out_435032814721793170[192] = 0;
   out_435032814721793170[193] = 0;
   out_435032814721793170[194] = 0;
   out_435032814721793170[195] = 0;
   out_435032814721793170[196] = 0;
   out_435032814721793170[197] = 0;
   out_435032814721793170[198] = 0;
   out_435032814721793170[199] = 0;
   out_435032814721793170[200] = 0;
   out_435032814721793170[201] = 0;
   out_435032814721793170[202] = 0;
   out_435032814721793170[203] = 0;
   out_435032814721793170[204] = 0;
   out_435032814721793170[205] = 0;
   out_435032814721793170[206] = 0;
   out_435032814721793170[207] = 0;
   out_435032814721793170[208] = 0;
   out_435032814721793170[209] = 1;
   out_435032814721793170[210] = 0;
   out_435032814721793170[211] = 0;
   out_435032814721793170[212] = 0;
   out_435032814721793170[213] = 0;
   out_435032814721793170[214] = 0;
   out_435032814721793170[215] = 0;
   out_435032814721793170[216] = 0;
   out_435032814721793170[217] = 0;
   out_435032814721793170[218] = 0;
   out_435032814721793170[219] = 0;
   out_435032814721793170[220] = 0;
   out_435032814721793170[221] = 0;
   out_435032814721793170[222] = 0;
   out_435032814721793170[223] = 0;
   out_435032814721793170[224] = 0;
   out_435032814721793170[225] = 0;
   out_435032814721793170[226] = 0;
   out_435032814721793170[227] = 0;
   out_435032814721793170[228] = 1;
   out_435032814721793170[229] = 0;
   out_435032814721793170[230] = 0;
   out_435032814721793170[231] = 0;
   out_435032814721793170[232] = 0;
   out_435032814721793170[233] = 0;
   out_435032814721793170[234] = 0;
   out_435032814721793170[235] = 0;
   out_435032814721793170[236] = 0;
   out_435032814721793170[237] = 0;
   out_435032814721793170[238] = 0;
   out_435032814721793170[239] = 0;
   out_435032814721793170[240] = 0;
   out_435032814721793170[241] = 0;
   out_435032814721793170[242] = 0;
   out_435032814721793170[243] = 0;
   out_435032814721793170[244] = 0;
   out_435032814721793170[245] = 0;
   out_435032814721793170[246] = 0;
   out_435032814721793170[247] = 1;
   out_435032814721793170[248] = 0;
   out_435032814721793170[249] = 0;
   out_435032814721793170[250] = 0;
   out_435032814721793170[251] = 0;
   out_435032814721793170[252] = 0;
   out_435032814721793170[253] = 0;
   out_435032814721793170[254] = 0;
   out_435032814721793170[255] = 0;
   out_435032814721793170[256] = 0;
   out_435032814721793170[257] = 0;
   out_435032814721793170[258] = 0;
   out_435032814721793170[259] = 0;
   out_435032814721793170[260] = 0;
   out_435032814721793170[261] = 0;
   out_435032814721793170[262] = 0;
   out_435032814721793170[263] = 0;
   out_435032814721793170[264] = 0;
   out_435032814721793170[265] = 0;
   out_435032814721793170[266] = 1;
   out_435032814721793170[267] = 0;
   out_435032814721793170[268] = 0;
   out_435032814721793170[269] = 0;
   out_435032814721793170[270] = 0;
   out_435032814721793170[271] = 0;
   out_435032814721793170[272] = 0;
   out_435032814721793170[273] = 0;
   out_435032814721793170[274] = 0;
   out_435032814721793170[275] = 0;
   out_435032814721793170[276] = 0;
   out_435032814721793170[277] = 0;
   out_435032814721793170[278] = 0;
   out_435032814721793170[279] = 0;
   out_435032814721793170[280] = 0;
   out_435032814721793170[281] = 0;
   out_435032814721793170[282] = 0;
   out_435032814721793170[283] = 0;
   out_435032814721793170[284] = 0;
   out_435032814721793170[285] = 1;
   out_435032814721793170[286] = 0;
   out_435032814721793170[287] = 0;
   out_435032814721793170[288] = 0;
   out_435032814721793170[289] = 0;
   out_435032814721793170[290] = 0;
   out_435032814721793170[291] = 0;
   out_435032814721793170[292] = 0;
   out_435032814721793170[293] = 0;
   out_435032814721793170[294] = 0;
   out_435032814721793170[295] = 0;
   out_435032814721793170[296] = 0;
   out_435032814721793170[297] = 0;
   out_435032814721793170[298] = 0;
   out_435032814721793170[299] = 0;
   out_435032814721793170[300] = 0;
   out_435032814721793170[301] = 0;
   out_435032814721793170[302] = 0;
   out_435032814721793170[303] = 0;
   out_435032814721793170[304] = 1;
   out_435032814721793170[305] = 0;
   out_435032814721793170[306] = 0;
   out_435032814721793170[307] = 0;
   out_435032814721793170[308] = 0;
   out_435032814721793170[309] = 0;
   out_435032814721793170[310] = 0;
   out_435032814721793170[311] = 0;
   out_435032814721793170[312] = 0;
   out_435032814721793170[313] = 0;
   out_435032814721793170[314] = 0;
   out_435032814721793170[315] = 0;
   out_435032814721793170[316] = 0;
   out_435032814721793170[317] = 0;
   out_435032814721793170[318] = 0;
   out_435032814721793170[319] = 0;
   out_435032814721793170[320] = 0;
   out_435032814721793170[321] = 0;
   out_435032814721793170[322] = 0;
   out_435032814721793170[323] = 1;
}
void h_4(double *state, double *unused, double *out_5120020554280573886) {
   out_5120020554280573886[0] = state[6] + state[9];
   out_5120020554280573886[1] = state[7] + state[10];
   out_5120020554280573886[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_6208770068591405626) {
   out_6208770068591405626[0] = 0;
   out_6208770068591405626[1] = 0;
   out_6208770068591405626[2] = 0;
   out_6208770068591405626[3] = 0;
   out_6208770068591405626[4] = 0;
   out_6208770068591405626[5] = 0;
   out_6208770068591405626[6] = 1;
   out_6208770068591405626[7] = 0;
   out_6208770068591405626[8] = 0;
   out_6208770068591405626[9] = 1;
   out_6208770068591405626[10] = 0;
   out_6208770068591405626[11] = 0;
   out_6208770068591405626[12] = 0;
   out_6208770068591405626[13] = 0;
   out_6208770068591405626[14] = 0;
   out_6208770068591405626[15] = 0;
   out_6208770068591405626[16] = 0;
   out_6208770068591405626[17] = 0;
   out_6208770068591405626[18] = 0;
   out_6208770068591405626[19] = 0;
   out_6208770068591405626[20] = 0;
   out_6208770068591405626[21] = 0;
   out_6208770068591405626[22] = 0;
   out_6208770068591405626[23] = 0;
   out_6208770068591405626[24] = 0;
   out_6208770068591405626[25] = 1;
   out_6208770068591405626[26] = 0;
   out_6208770068591405626[27] = 0;
   out_6208770068591405626[28] = 1;
   out_6208770068591405626[29] = 0;
   out_6208770068591405626[30] = 0;
   out_6208770068591405626[31] = 0;
   out_6208770068591405626[32] = 0;
   out_6208770068591405626[33] = 0;
   out_6208770068591405626[34] = 0;
   out_6208770068591405626[35] = 0;
   out_6208770068591405626[36] = 0;
   out_6208770068591405626[37] = 0;
   out_6208770068591405626[38] = 0;
   out_6208770068591405626[39] = 0;
   out_6208770068591405626[40] = 0;
   out_6208770068591405626[41] = 0;
   out_6208770068591405626[42] = 0;
   out_6208770068591405626[43] = 0;
   out_6208770068591405626[44] = 1;
   out_6208770068591405626[45] = 0;
   out_6208770068591405626[46] = 0;
   out_6208770068591405626[47] = 1;
   out_6208770068591405626[48] = 0;
   out_6208770068591405626[49] = 0;
   out_6208770068591405626[50] = 0;
   out_6208770068591405626[51] = 0;
   out_6208770068591405626[52] = 0;
   out_6208770068591405626[53] = 0;
}
void h_10(double *state, double *unused, double *out_1855806828650009923) {
   out_1855806828650009923[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1855806828650009923[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1855806828650009923[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_86752177367218496) {
   out_86752177367218496[0] = 0;
   out_86752177367218496[1] = 9.8100000000000005*cos(state[1]);
   out_86752177367218496[2] = 0;
   out_86752177367218496[3] = 0;
   out_86752177367218496[4] = -state[8];
   out_86752177367218496[5] = state[7];
   out_86752177367218496[6] = 0;
   out_86752177367218496[7] = state[5];
   out_86752177367218496[8] = -state[4];
   out_86752177367218496[9] = 0;
   out_86752177367218496[10] = 0;
   out_86752177367218496[11] = 0;
   out_86752177367218496[12] = 1;
   out_86752177367218496[13] = 0;
   out_86752177367218496[14] = 0;
   out_86752177367218496[15] = 1;
   out_86752177367218496[16] = 0;
   out_86752177367218496[17] = 0;
   out_86752177367218496[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_86752177367218496[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_86752177367218496[20] = 0;
   out_86752177367218496[21] = state[8];
   out_86752177367218496[22] = 0;
   out_86752177367218496[23] = -state[6];
   out_86752177367218496[24] = -state[5];
   out_86752177367218496[25] = 0;
   out_86752177367218496[26] = state[3];
   out_86752177367218496[27] = 0;
   out_86752177367218496[28] = 0;
   out_86752177367218496[29] = 0;
   out_86752177367218496[30] = 0;
   out_86752177367218496[31] = 1;
   out_86752177367218496[32] = 0;
   out_86752177367218496[33] = 0;
   out_86752177367218496[34] = 1;
   out_86752177367218496[35] = 0;
   out_86752177367218496[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_86752177367218496[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_86752177367218496[38] = 0;
   out_86752177367218496[39] = -state[7];
   out_86752177367218496[40] = state[6];
   out_86752177367218496[41] = 0;
   out_86752177367218496[42] = state[4];
   out_86752177367218496[43] = -state[3];
   out_86752177367218496[44] = 0;
   out_86752177367218496[45] = 0;
   out_86752177367218496[46] = 0;
   out_86752177367218496[47] = 0;
   out_86752177367218496[48] = 0;
   out_86752177367218496[49] = 0;
   out_86752177367218496[50] = 1;
   out_86752177367218496[51] = 0;
   out_86752177367218496[52] = 0;
   out_86752177367218496[53] = 1;
}
void h_13(double *state, double *unused, double *out_3472048471963902900) {
   out_3472048471963902900[0] = state[3];
   out_3472048471963902900[1] = state[4];
   out_3472048471963902900[2] = state[5];
}
void H_13(double *state, double *unused, double *out_9025700179785813189) {
   out_9025700179785813189[0] = 0;
   out_9025700179785813189[1] = 0;
   out_9025700179785813189[2] = 0;
   out_9025700179785813189[3] = 1;
   out_9025700179785813189[4] = 0;
   out_9025700179785813189[5] = 0;
   out_9025700179785813189[6] = 0;
   out_9025700179785813189[7] = 0;
   out_9025700179785813189[8] = 0;
   out_9025700179785813189[9] = 0;
   out_9025700179785813189[10] = 0;
   out_9025700179785813189[11] = 0;
   out_9025700179785813189[12] = 0;
   out_9025700179785813189[13] = 0;
   out_9025700179785813189[14] = 0;
   out_9025700179785813189[15] = 0;
   out_9025700179785813189[16] = 0;
   out_9025700179785813189[17] = 0;
   out_9025700179785813189[18] = 0;
   out_9025700179785813189[19] = 0;
   out_9025700179785813189[20] = 0;
   out_9025700179785813189[21] = 0;
   out_9025700179785813189[22] = 1;
   out_9025700179785813189[23] = 0;
   out_9025700179785813189[24] = 0;
   out_9025700179785813189[25] = 0;
   out_9025700179785813189[26] = 0;
   out_9025700179785813189[27] = 0;
   out_9025700179785813189[28] = 0;
   out_9025700179785813189[29] = 0;
   out_9025700179785813189[30] = 0;
   out_9025700179785813189[31] = 0;
   out_9025700179785813189[32] = 0;
   out_9025700179785813189[33] = 0;
   out_9025700179785813189[34] = 0;
   out_9025700179785813189[35] = 0;
   out_9025700179785813189[36] = 0;
   out_9025700179785813189[37] = 0;
   out_9025700179785813189[38] = 0;
   out_9025700179785813189[39] = 0;
   out_9025700179785813189[40] = 0;
   out_9025700179785813189[41] = 1;
   out_9025700179785813189[42] = 0;
   out_9025700179785813189[43] = 0;
   out_9025700179785813189[44] = 0;
   out_9025700179785813189[45] = 0;
   out_9025700179785813189[46] = 0;
   out_9025700179785813189[47] = 0;
   out_9025700179785813189[48] = 0;
   out_9025700179785813189[49] = 0;
   out_9025700179785813189[50] = 0;
   out_9025700179785813189[51] = 0;
   out_9025700179785813189[52] = 0;
   out_9025700179785813189[53] = 0;
}
void h_14(double *state, double *unused, double *out_1446434657591522405) {
   out_1446434657591522405[0] = state[6];
   out_1446434657591522405[1] = state[7];
   out_1446434657591522405[2] = state[8];
}
void H_14(double *state, double *unused, double *out_8274733148778661461) {
   out_8274733148778661461[0] = 0;
   out_8274733148778661461[1] = 0;
   out_8274733148778661461[2] = 0;
   out_8274733148778661461[3] = 0;
   out_8274733148778661461[4] = 0;
   out_8274733148778661461[5] = 0;
   out_8274733148778661461[6] = 1;
   out_8274733148778661461[7] = 0;
   out_8274733148778661461[8] = 0;
   out_8274733148778661461[9] = 0;
   out_8274733148778661461[10] = 0;
   out_8274733148778661461[11] = 0;
   out_8274733148778661461[12] = 0;
   out_8274733148778661461[13] = 0;
   out_8274733148778661461[14] = 0;
   out_8274733148778661461[15] = 0;
   out_8274733148778661461[16] = 0;
   out_8274733148778661461[17] = 0;
   out_8274733148778661461[18] = 0;
   out_8274733148778661461[19] = 0;
   out_8274733148778661461[20] = 0;
   out_8274733148778661461[21] = 0;
   out_8274733148778661461[22] = 0;
   out_8274733148778661461[23] = 0;
   out_8274733148778661461[24] = 0;
   out_8274733148778661461[25] = 1;
   out_8274733148778661461[26] = 0;
   out_8274733148778661461[27] = 0;
   out_8274733148778661461[28] = 0;
   out_8274733148778661461[29] = 0;
   out_8274733148778661461[30] = 0;
   out_8274733148778661461[31] = 0;
   out_8274733148778661461[32] = 0;
   out_8274733148778661461[33] = 0;
   out_8274733148778661461[34] = 0;
   out_8274733148778661461[35] = 0;
   out_8274733148778661461[36] = 0;
   out_8274733148778661461[37] = 0;
   out_8274733148778661461[38] = 0;
   out_8274733148778661461[39] = 0;
   out_8274733148778661461[40] = 0;
   out_8274733148778661461[41] = 0;
   out_8274733148778661461[42] = 0;
   out_8274733148778661461[43] = 0;
   out_8274733148778661461[44] = 1;
   out_8274733148778661461[45] = 0;
   out_8274733148778661461[46] = 0;
   out_8274733148778661461[47] = 0;
   out_8274733148778661461[48] = 0;
   out_8274733148778661461[49] = 0;
   out_8274733148778661461[50] = 0;
   out_8274733148778661461[51] = 0;
   out_8274733148778661461[52] = 0;
   out_8274733148778661461[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8427200704796300077) {
  err_fun(nom_x, delta_x, out_8427200704796300077);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_209888032840788679) {
  inv_err_fun(nom_x, true_x, out_209888032840788679);
}
void pose_H_mod_fun(double *state, double *out_5010822586708507522) {
  H_mod_fun(state, out_5010822586708507522);
}
void pose_f_fun(double *state, double dt, double *out_8028362113385460735) {
  f_fun(state,  dt, out_8028362113385460735);
}
void pose_F_fun(double *state, double dt, double *out_435032814721793170) {
  F_fun(state,  dt, out_435032814721793170);
}
void pose_h_4(double *state, double *unused, double *out_5120020554280573886) {
  h_4(state, unused, out_5120020554280573886);
}
void pose_H_4(double *state, double *unused, double *out_6208770068591405626) {
  H_4(state, unused, out_6208770068591405626);
}
void pose_h_10(double *state, double *unused, double *out_1855806828650009923) {
  h_10(state, unused, out_1855806828650009923);
}
void pose_H_10(double *state, double *unused, double *out_86752177367218496) {
  H_10(state, unused, out_86752177367218496);
}
void pose_h_13(double *state, double *unused, double *out_3472048471963902900) {
  h_13(state, unused, out_3472048471963902900);
}
void pose_H_13(double *state, double *unused, double *out_9025700179785813189) {
  H_13(state, unused, out_9025700179785813189);
}
void pose_h_14(double *state, double *unused, double *out_1446434657591522405) {
  h_14(state, unused, out_1446434657591522405);
}
void pose_H_14(double *state, double *unused, double *out_8274733148778661461) {
  H_14(state, unused, out_8274733148778661461);
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
