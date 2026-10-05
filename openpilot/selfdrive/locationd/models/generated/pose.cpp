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
void err_fun(double *nom_x, double *delta_x, double *out_2897896323809259494) {
   out_2897896323809259494[0] = delta_x[0] + nom_x[0];
   out_2897896323809259494[1] = delta_x[1] + nom_x[1];
   out_2897896323809259494[2] = delta_x[2] + nom_x[2];
   out_2897896323809259494[3] = delta_x[3] + nom_x[3];
   out_2897896323809259494[4] = delta_x[4] + nom_x[4];
   out_2897896323809259494[5] = delta_x[5] + nom_x[5];
   out_2897896323809259494[6] = delta_x[6] + nom_x[6];
   out_2897896323809259494[7] = delta_x[7] + nom_x[7];
   out_2897896323809259494[8] = delta_x[8] + nom_x[8];
   out_2897896323809259494[9] = delta_x[9] + nom_x[9];
   out_2897896323809259494[10] = delta_x[10] + nom_x[10];
   out_2897896323809259494[11] = delta_x[11] + nom_x[11];
   out_2897896323809259494[12] = delta_x[12] + nom_x[12];
   out_2897896323809259494[13] = delta_x[13] + nom_x[13];
   out_2897896323809259494[14] = delta_x[14] + nom_x[14];
   out_2897896323809259494[15] = delta_x[15] + nom_x[15];
   out_2897896323809259494[16] = delta_x[16] + nom_x[16];
   out_2897896323809259494[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6584763988727841558) {
   out_6584763988727841558[0] = -nom_x[0] + true_x[0];
   out_6584763988727841558[1] = -nom_x[1] + true_x[1];
   out_6584763988727841558[2] = -nom_x[2] + true_x[2];
   out_6584763988727841558[3] = -nom_x[3] + true_x[3];
   out_6584763988727841558[4] = -nom_x[4] + true_x[4];
   out_6584763988727841558[5] = -nom_x[5] + true_x[5];
   out_6584763988727841558[6] = -nom_x[6] + true_x[6];
   out_6584763988727841558[7] = -nom_x[7] + true_x[7];
   out_6584763988727841558[8] = -nom_x[8] + true_x[8];
   out_6584763988727841558[9] = -nom_x[9] + true_x[9];
   out_6584763988727841558[10] = -nom_x[10] + true_x[10];
   out_6584763988727841558[11] = -nom_x[11] + true_x[11];
   out_6584763988727841558[12] = -nom_x[12] + true_x[12];
   out_6584763988727841558[13] = -nom_x[13] + true_x[13];
   out_6584763988727841558[14] = -nom_x[14] + true_x[14];
   out_6584763988727841558[15] = -nom_x[15] + true_x[15];
   out_6584763988727841558[16] = -nom_x[16] + true_x[16];
   out_6584763988727841558[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5860240321001220316) {
   out_5860240321001220316[0] = 1.0;
   out_5860240321001220316[1] = 0.0;
   out_5860240321001220316[2] = 0.0;
   out_5860240321001220316[3] = 0.0;
   out_5860240321001220316[4] = 0.0;
   out_5860240321001220316[5] = 0.0;
   out_5860240321001220316[6] = 0.0;
   out_5860240321001220316[7] = 0.0;
   out_5860240321001220316[8] = 0.0;
   out_5860240321001220316[9] = 0.0;
   out_5860240321001220316[10] = 0.0;
   out_5860240321001220316[11] = 0.0;
   out_5860240321001220316[12] = 0.0;
   out_5860240321001220316[13] = 0.0;
   out_5860240321001220316[14] = 0.0;
   out_5860240321001220316[15] = 0.0;
   out_5860240321001220316[16] = 0.0;
   out_5860240321001220316[17] = 0.0;
   out_5860240321001220316[18] = 0.0;
   out_5860240321001220316[19] = 1.0;
   out_5860240321001220316[20] = 0.0;
   out_5860240321001220316[21] = 0.0;
   out_5860240321001220316[22] = 0.0;
   out_5860240321001220316[23] = 0.0;
   out_5860240321001220316[24] = 0.0;
   out_5860240321001220316[25] = 0.0;
   out_5860240321001220316[26] = 0.0;
   out_5860240321001220316[27] = 0.0;
   out_5860240321001220316[28] = 0.0;
   out_5860240321001220316[29] = 0.0;
   out_5860240321001220316[30] = 0.0;
   out_5860240321001220316[31] = 0.0;
   out_5860240321001220316[32] = 0.0;
   out_5860240321001220316[33] = 0.0;
   out_5860240321001220316[34] = 0.0;
   out_5860240321001220316[35] = 0.0;
   out_5860240321001220316[36] = 0.0;
   out_5860240321001220316[37] = 0.0;
   out_5860240321001220316[38] = 1.0;
   out_5860240321001220316[39] = 0.0;
   out_5860240321001220316[40] = 0.0;
   out_5860240321001220316[41] = 0.0;
   out_5860240321001220316[42] = 0.0;
   out_5860240321001220316[43] = 0.0;
   out_5860240321001220316[44] = 0.0;
   out_5860240321001220316[45] = 0.0;
   out_5860240321001220316[46] = 0.0;
   out_5860240321001220316[47] = 0.0;
   out_5860240321001220316[48] = 0.0;
   out_5860240321001220316[49] = 0.0;
   out_5860240321001220316[50] = 0.0;
   out_5860240321001220316[51] = 0.0;
   out_5860240321001220316[52] = 0.0;
   out_5860240321001220316[53] = 0.0;
   out_5860240321001220316[54] = 0.0;
   out_5860240321001220316[55] = 0.0;
   out_5860240321001220316[56] = 0.0;
   out_5860240321001220316[57] = 1.0;
   out_5860240321001220316[58] = 0.0;
   out_5860240321001220316[59] = 0.0;
   out_5860240321001220316[60] = 0.0;
   out_5860240321001220316[61] = 0.0;
   out_5860240321001220316[62] = 0.0;
   out_5860240321001220316[63] = 0.0;
   out_5860240321001220316[64] = 0.0;
   out_5860240321001220316[65] = 0.0;
   out_5860240321001220316[66] = 0.0;
   out_5860240321001220316[67] = 0.0;
   out_5860240321001220316[68] = 0.0;
   out_5860240321001220316[69] = 0.0;
   out_5860240321001220316[70] = 0.0;
   out_5860240321001220316[71] = 0.0;
   out_5860240321001220316[72] = 0.0;
   out_5860240321001220316[73] = 0.0;
   out_5860240321001220316[74] = 0.0;
   out_5860240321001220316[75] = 0.0;
   out_5860240321001220316[76] = 1.0;
   out_5860240321001220316[77] = 0.0;
   out_5860240321001220316[78] = 0.0;
   out_5860240321001220316[79] = 0.0;
   out_5860240321001220316[80] = 0.0;
   out_5860240321001220316[81] = 0.0;
   out_5860240321001220316[82] = 0.0;
   out_5860240321001220316[83] = 0.0;
   out_5860240321001220316[84] = 0.0;
   out_5860240321001220316[85] = 0.0;
   out_5860240321001220316[86] = 0.0;
   out_5860240321001220316[87] = 0.0;
   out_5860240321001220316[88] = 0.0;
   out_5860240321001220316[89] = 0.0;
   out_5860240321001220316[90] = 0.0;
   out_5860240321001220316[91] = 0.0;
   out_5860240321001220316[92] = 0.0;
   out_5860240321001220316[93] = 0.0;
   out_5860240321001220316[94] = 0.0;
   out_5860240321001220316[95] = 1.0;
   out_5860240321001220316[96] = 0.0;
   out_5860240321001220316[97] = 0.0;
   out_5860240321001220316[98] = 0.0;
   out_5860240321001220316[99] = 0.0;
   out_5860240321001220316[100] = 0.0;
   out_5860240321001220316[101] = 0.0;
   out_5860240321001220316[102] = 0.0;
   out_5860240321001220316[103] = 0.0;
   out_5860240321001220316[104] = 0.0;
   out_5860240321001220316[105] = 0.0;
   out_5860240321001220316[106] = 0.0;
   out_5860240321001220316[107] = 0.0;
   out_5860240321001220316[108] = 0.0;
   out_5860240321001220316[109] = 0.0;
   out_5860240321001220316[110] = 0.0;
   out_5860240321001220316[111] = 0.0;
   out_5860240321001220316[112] = 0.0;
   out_5860240321001220316[113] = 0.0;
   out_5860240321001220316[114] = 1.0;
   out_5860240321001220316[115] = 0.0;
   out_5860240321001220316[116] = 0.0;
   out_5860240321001220316[117] = 0.0;
   out_5860240321001220316[118] = 0.0;
   out_5860240321001220316[119] = 0.0;
   out_5860240321001220316[120] = 0.0;
   out_5860240321001220316[121] = 0.0;
   out_5860240321001220316[122] = 0.0;
   out_5860240321001220316[123] = 0.0;
   out_5860240321001220316[124] = 0.0;
   out_5860240321001220316[125] = 0.0;
   out_5860240321001220316[126] = 0.0;
   out_5860240321001220316[127] = 0.0;
   out_5860240321001220316[128] = 0.0;
   out_5860240321001220316[129] = 0.0;
   out_5860240321001220316[130] = 0.0;
   out_5860240321001220316[131] = 0.0;
   out_5860240321001220316[132] = 0.0;
   out_5860240321001220316[133] = 1.0;
   out_5860240321001220316[134] = 0.0;
   out_5860240321001220316[135] = 0.0;
   out_5860240321001220316[136] = 0.0;
   out_5860240321001220316[137] = 0.0;
   out_5860240321001220316[138] = 0.0;
   out_5860240321001220316[139] = 0.0;
   out_5860240321001220316[140] = 0.0;
   out_5860240321001220316[141] = 0.0;
   out_5860240321001220316[142] = 0.0;
   out_5860240321001220316[143] = 0.0;
   out_5860240321001220316[144] = 0.0;
   out_5860240321001220316[145] = 0.0;
   out_5860240321001220316[146] = 0.0;
   out_5860240321001220316[147] = 0.0;
   out_5860240321001220316[148] = 0.0;
   out_5860240321001220316[149] = 0.0;
   out_5860240321001220316[150] = 0.0;
   out_5860240321001220316[151] = 0.0;
   out_5860240321001220316[152] = 1.0;
   out_5860240321001220316[153] = 0.0;
   out_5860240321001220316[154] = 0.0;
   out_5860240321001220316[155] = 0.0;
   out_5860240321001220316[156] = 0.0;
   out_5860240321001220316[157] = 0.0;
   out_5860240321001220316[158] = 0.0;
   out_5860240321001220316[159] = 0.0;
   out_5860240321001220316[160] = 0.0;
   out_5860240321001220316[161] = 0.0;
   out_5860240321001220316[162] = 0.0;
   out_5860240321001220316[163] = 0.0;
   out_5860240321001220316[164] = 0.0;
   out_5860240321001220316[165] = 0.0;
   out_5860240321001220316[166] = 0.0;
   out_5860240321001220316[167] = 0.0;
   out_5860240321001220316[168] = 0.0;
   out_5860240321001220316[169] = 0.0;
   out_5860240321001220316[170] = 0.0;
   out_5860240321001220316[171] = 1.0;
   out_5860240321001220316[172] = 0.0;
   out_5860240321001220316[173] = 0.0;
   out_5860240321001220316[174] = 0.0;
   out_5860240321001220316[175] = 0.0;
   out_5860240321001220316[176] = 0.0;
   out_5860240321001220316[177] = 0.0;
   out_5860240321001220316[178] = 0.0;
   out_5860240321001220316[179] = 0.0;
   out_5860240321001220316[180] = 0.0;
   out_5860240321001220316[181] = 0.0;
   out_5860240321001220316[182] = 0.0;
   out_5860240321001220316[183] = 0.0;
   out_5860240321001220316[184] = 0.0;
   out_5860240321001220316[185] = 0.0;
   out_5860240321001220316[186] = 0.0;
   out_5860240321001220316[187] = 0.0;
   out_5860240321001220316[188] = 0.0;
   out_5860240321001220316[189] = 0.0;
   out_5860240321001220316[190] = 1.0;
   out_5860240321001220316[191] = 0.0;
   out_5860240321001220316[192] = 0.0;
   out_5860240321001220316[193] = 0.0;
   out_5860240321001220316[194] = 0.0;
   out_5860240321001220316[195] = 0.0;
   out_5860240321001220316[196] = 0.0;
   out_5860240321001220316[197] = 0.0;
   out_5860240321001220316[198] = 0.0;
   out_5860240321001220316[199] = 0.0;
   out_5860240321001220316[200] = 0.0;
   out_5860240321001220316[201] = 0.0;
   out_5860240321001220316[202] = 0.0;
   out_5860240321001220316[203] = 0.0;
   out_5860240321001220316[204] = 0.0;
   out_5860240321001220316[205] = 0.0;
   out_5860240321001220316[206] = 0.0;
   out_5860240321001220316[207] = 0.0;
   out_5860240321001220316[208] = 0.0;
   out_5860240321001220316[209] = 1.0;
   out_5860240321001220316[210] = 0.0;
   out_5860240321001220316[211] = 0.0;
   out_5860240321001220316[212] = 0.0;
   out_5860240321001220316[213] = 0.0;
   out_5860240321001220316[214] = 0.0;
   out_5860240321001220316[215] = 0.0;
   out_5860240321001220316[216] = 0.0;
   out_5860240321001220316[217] = 0.0;
   out_5860240321001220316[218] = 0.0;
   out_5860240321001220316[219] = 0.0;
   out_5860240321001220316[220] = 0.0;
   out_5860240321001220316[221] = 0.0;
   out_5860240321001220316[222] = 0.0;
   out_5860240321001220316[223] = 0.0;
   out_5860240321001220316[224] = 0.0;
   out_5860240321001220316[225] = 0.0;
   out_5860240321001220316[226] = 0.0;
   out_5860240321001220316[227] = 0.0;
   out_5860240321001220316[228] = 1.0;
   out_5860240321001220316[229] = 0.0;
   out_5860240321001220316[230] = 0.0;
   out_5860240321001220316[231] = 0.0;
   out_5860240321001220316[232] = 0.0;
   out_5860240321001220316[233] = 0.0;
   out_5860240321001220316[234] = 0.0;
   out_5860240321001220316[235] = 0.0;
   out_5860240321001220316[236] = 0.0;
   out_5860240321001220316[237] = 0.0;
   out_5860240321001220316[238] = 0.0;
   out_5860240321001220316[239] = 0.0;
   out_5860240321001220316[240] = 0.0;
   out_5860240321001220316[241] = 0.0;
   out_5860240321001220316[242] = 0.0;
   out_5860240321001220316[243] = 0.0;
   out_5860240321001220316[244] = 0.0;
   out_5860240321001220316[245] = 0.0;
   out_5860240321001220316[246] = 0.0;
   out_5860240321001220316[247] = 1.0;
   out_5860240321001220316[248] = 0.0;
   out_5860240321001220316[249] = 0.0;
   out_5860240321001220316[250] = 0.0;
   out_5860240321001220316[251] = 0.0;
   out_5860240321001220316[252] = 0.0;
   out_5860240321001220316[253] = 0.0;
   out_5860240321001220316[254] = 0.0;
   out_5860240321001220316[255] = 0.0;
   out_5860240321001220316[256] = 0.0;
   out_5860240321001220316[257] = 0.0;
   out_5860240321001220316[258] = 0.0;
   out_5860240321001220316[259] = 0.0;
   out_5860240321001220316[260] = 0.0;
   out_5860240321001220316[261] = 0.0;
   out_5860240321001220316[262] = 0.0;
   out_5860240321001220316[263] = 0.0;
   out_5860240321001220316[264] = 0.0;
   out_5860240321001220316[265] = 0.0;
   out_5860240321001220316[266] = 1.0;
   out_5860240321001220316[267] = 0.0;
   out_5860240321001220316[268] = 0.0;
   out_5860240321001220316[269] = 0.0;
   out_5860240321001220316[270] = 0.0;
   out_5860240321001220316[271] = 0.0;
   out_5860240321001220316[272] = 0.0;
   out_5860240321001220316[273] = 0.0;
   out_5860240321001220316[274] = 0.0;
   out_5860240321001220316[275] = 0.0;
   out_5860240321001220316[276] = 0.0;
   out_5860240321001220316[277] = 0.0;
   out_5860240321001220316[278] = 0.0;
   out_5860240321001220316[279] = 0.0;
   out_5860240321001220316[280] = 0.0;
   out_5860240321001220316[281] = 0.0;
   out_5860240321001220316[282] = 0.0;
   out_5860240321001220316[283] = 0.0;
   out_5860240321001220316[284] = 0.0;
   out_5860240321001220316[285] = 1.0;
   out_5860240321001220316[286] = 0.0;
   out_5860240321001220316[287] = 0.0;
   out_5860240321001220316[288] = 0.0;
   out_5860240321001220316[289] = 0.0;
   out_5860240321001220316[290] = 0.0;
   out_5860240321001220316[291] = 0.0;
   out_5860240321001220316[292] = 0.0;
   out_5860240321001220316[293] = 0.0;
   out_5860240321001220316[294] = 0.0;
   out_5860240321001220316[295] = 0.0;
   out_5860240321001220316[296] = 0.0;
   out_5860240321001220316[297] = 0.0;
   out_5860240321001220316[298] = 0.0;
   out_5860240321001220316[299] = 0.0;
   out_5860240321001220316[300] = 0.0;
   out_5860240321001220316[301] = 0.0;
   out_5860240321001220316[302] = 0.0;
   out_5860240321001220316[303] = 0.0;
   out_5860240321001220316[304] = 1.0;
   out_5860240321001220316[305] = 0.0;
   out_5860240321001220316[306] = 0.0;
   out_5860240321001220316[307] = 0.0;
   out_5860240321001220316[308] = 0.0;
   out_5860240321001220316[309] = 0.0;
   out_5860240321001220316[310] = 0.0;
   out_5860240321001220316[311] = 0.0;
   out_5860240321001220316[312] = 0.0;
   out_5860240321001220316[313] = 0.0;
   out_5860240321001220316[314] = 0.0;
   out_5860240321001220316[315] = 0.0;
   out_5860240321001220316[316] = 0.0;
   out_5860240321001220316[317] = 0.0;
   out_5860240321001220316[318] = 0.0;
   out_5860240321001220316[319] = 0.0;
   out_5860240321001220316[320] = 0.0;
   out_5860240321001220316[321] = 0.0;
   out_5860240321001220316[322] = 0.0;
   out_5860240321001220316[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5165064222563725696) {
   out_5165064222563725696[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5165064222563725696[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5165064222563725696[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5165064222563725696[3] = dt*state[12] + state[3];
   out_5165064222563725696[4] = dt*state[13] + state[4];
   out_5165064222563725696[5] = dt*state[14] + state[5];
   out_5165064222563725696[6] = state[6];
   out_5165064222563725696[7] = state[7];
   out_5165064222563725696[8] = state[8];
   out_5165064222563725696[9] = state[9];
   out_5165064222563725696[10] = state[10];
   out_5165064222563725696[11] = state[11];
   out_5165064222563725696[12] = state[12];
   out_5165064222563725696[13] = state[13];
   out_5165064222563725696[14] = state[14];
   out_5165064222563725696[15] = state[15];
   out_5165064222563725696[16] = state[16];
   out_5165064222563725696[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6599370070449602621) {
   out_6599370070449602621[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6599370070449602621[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6599370070449602621[2] = 0;
   out_6599370070449602621[3] = 0;
   out_6599370070449602621[4] = 0;
   out_6599370070449602621[5] = 0;
   out_6599370070449602621[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6599370070449602621[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6599370070449602621[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6599370070449602621[9] = 0;
   out_6599370070449602621[10] = 0;
   out_6599370070449602621[11] = 0;
   out_6599370070449602621[12] = 0;
   out_6599370070449602621[13] = 0;
   out_6599370070449602621[14] = 0;
   out_6599370070449602621[15] = 0;
   out_6599370070449602621[16] = 0;
   out_6599370070449602621[17] = 0;
   out_6599370070449602621[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6599370070449602621[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6599370070449602621[20] = 0;
   out_6599370070449602621[21] = 0;
   out_6599370070449602621[22] = 0;
   out_6599370070449602621[23] = 0;
   out_6599370070449602621[24] = 0;
   out_6599370070449602621[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6599370070449602621[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6599370070449602621[27] = 0;
   out_6599370070449602621[28] = 0;
   out_6599370070449602621[29] = 0;
   out_6599370070449602621[30] = 0;
   out_6599370070449602621[31] = 0;
   out_6599370070449602621[32] = 0;
   out_6599370070449602621[33] = 0;
   out_6599370070449602621[34] = 0;
   out_6599370070449602621[35] = 0;
   out_6599370070449602621[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6599370070449602621[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6599370070449602621[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6599370070449602621[39] = 0;
   out_6599370070449602621[40] = 0;
   out_6599370070449602621[41] = 0;
   out_6599370070449602621[42] = 0;
   out_6599370070449602621[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6599370070449602621[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6599370070449602621[45] = 0;
   out_6599370070449602621[46] = 0;
   out_6599370070449602621[47] = 0;
   out_6599370070449602621[48] = 0;
   out_6599370070449602621[49] = 0;
   out_6599370070449602621[50] = 0;
   out_6599370070449602621[51] = 0;
   out_6599370070449602621[52] = 0;
   out_6599370070449602621[53] = 0;
   out_6599370070449602621[54] = 0;
   out_6599370070449602621[55] = 0;
   out_6599370070449602621[56] = 0;
   out_6599370070449602621[57] = 1;
   out_6599370070449602621[58] = 0;
   out_6599370070449602621[59] = 0;
   out_6599370070449602621[60] = 0;
   out_6599370070449602621[61] = 0;
   out_6599370070449602621[62] = 0;
   out_6599370070449602621[63] = 0;
   out_6599370070449602621[64] = 0;
   out_6599370070449602621[65] = 0;
   out_6599370070449602621[66] = dt;
   out_6599370070449602621[67] = 0;
   out_6599370070449602621[68] = 0;
   out_6599370070449602621[69] = 0;
   out_6599370070449602621[70] = 0;
   out_6599370070449602621[71] = 0;
   out_6599370070449602621[72] = 0;
   out_6599370070449602621[73] = 0;
   out_6599370070449602621[74] = 0;
   out_6599370070449602621[75] = 0;
   out_6599370070449602621[76] = 1;
   out_6599370070449602621[77] = 0;
   out_6599370070449602621[78] = 0;
   out_6599370070449602621[79] = 0;
   out_6599370070449602621[80] = 0;
   out_6599370070449602621[81] = 0;
   out_6599370070449602621[82] = 0;
   out_6599370070449602621[83] = 0;
   out_6599370070449602621[84] = 0;
   out_6599370070449602621[85] = dt;
   out_6599370070449602621[86] = 0;
   out_6599370070449602621[87] = 0;
   out_6599370070449602621[88] = 0;
   out_6599370070449602621[89] = 0;
   out_6599370070449602621[90] = 0;
   out_6599370070449602621[91] = 0;
   out_6599370070449602621[92] = 0;
   out_6599370070449602621[93] = 0;
   out_6599370070449602621[94] = 0;
   out_6599370070449602621[95] = 1;
   out_6599370070449602621[96] = 0;
   out_6599370070449602621[97] = 0;
   out_6599370070449602621[98] = 0;
   out_6599370070449602621[99] = 0;
   out_6599370070449602621[100] = 0;
   out_6599370070449602621[101] = 0;
   out_6599370070449602621[102] = 0;
   out_6599370070449602621[103] = 0;
   out_6599370070449602621[104] = dt;
   out_6599370070449602621[105] = 0;
   out_6599370070449602621[106] = 0;
   out_6599370070449602621[107] = 0;
   out_6599370070449602621[108] = 0;
   out_6599370070449602621[109] = 0;
   out_6599370070449602621[110] = 0;
   out_6599370070449602621[111] = 0;
   out_6599370070449602621[112] = 0;
   out_6599370070449602621[113] = 0;
   out_6599370070449602621[114] = 1;
   out_6599370070449602621[115] = 0;
   out_6599370070449602621[116] = 0;
   out_6599370070449602621[117] = 0;
   out_6599370070449602621[118] = 0;
   out_6599370070449602621[119] = 0;
   out_6599370070449602621[120] = 0;
   out_6599370070449602621[121] = 0;
   out_6599370070449602621[122] = 0;
   out_6599370070449602621[123] = 0;
   out_6599370070449602621[124] = 0;
   out_6599370070449602621[125] = 0;
   out_6599370070449602621[126] = 0;
   out_6599370070449602621[127] = 0;
   out_6599370070449602621[128] = 0;
   out_6599370070449602621[129] = 0;
   out_6599370070449602621[130] = 0;
   out_6599370070449602621[131] = 0;
   out_6599370070449602621[132] = 0;
   out_6599370070449602621[133] = 1;
   out_6599370070449602621[134] = 0;
   out_6599370070449602621[135] = 0;
   out_6599370070449602621[136] = 0;
   out_6599370070449602621[137] = 0;
   out_6599370070449602621[138] = 0;
   out_6599370070449602621[139] = 0;
   out_6599370070449602621[140] = 0;
   out_6599370070449602621[141] = 0;
   out_6599370070449602621[142] = 0;
   out_6599370070449602621[143] = 0;
   out_6599370070449602621[144] = 0;
   out_6599370070449602621[145] = 0;
   out_6599370070449602621[146] = 0;
   out_6599370070449602621[147] = 0;
   out_6599370070449602621[148] = 0;
   out_6599370070449602621[149] = 0;
   out_6599370070449602621[150] = 0;
   out_6599370070449602621[151] = 0;
   out_6599370070449602621[152] = 1;
   out_6599370070449602621[153] = 0;
   out_6599370070449602621[154] = 0;
   out_6599370070449602621[155] = 0;
   out_6599370070449602621[156] = 0;
   out_6599370070449602621[157] = 0;
   out_6599370070449602621[158] = 0;
   out_6599370070449602621[159] = 0;
   out_6599370070449602621[160] = 0;
   out_6599370070449602621[161] = 0;
   out_6599370070449602621[162] = 0;
   out_6599370070449602621[163] = 0;
   out_6599370070449602621[164] = 0;
   out_6599370070449602621[165] = 0;
   out_6599370070449602621[166] = 0;
   out_6599370070449602621[167] = 0;
   out_6599370070449602621[168] = 0;
   out_6599370070449602621[169] = 0;
   out_6599370070449602621[170] = 0;
   out_6599370070449602621[171] = 1;
   out_6599370070449602621[172] = 0;
   out_6599370070449602621[173] = 0;
   out_6599370070449602621[174] = 0;
   out_6599370070449602621[175] = 0;
   out_6599370070449602621[176] = 0;
   out_6599370070449602621[177] = 0;
   out_6599370070449602621[178] = 0;
   out_6599370070449602621[179] = 0;
   out_6599370070449602621[180] = 0;
   out_6599370070449602621[181] = 0;
   out_6599370070449602621[182] = 0;
   out_6599370070449602621[183] = 0;
   out_6599370070449602621[184] = 0;
   out_6599370070449602621[185] = 0;
   out_6599370070449602621[186] = 0;
   out_6599370070449602621[187] = 0;
   out_6599370070449602621[188] = 0;
   out_6599370070449602621[189] = 0;
   out_6599370070449602621[190] = 1;
   out_6599370070449602621[191] = 0;
   out_6599370070449602621[192] = 0;
   out_6599370070449602621[193] = 0;
   out_6599370070449602621[194] = 0;
   out_6599370070449602621[195] = 0;
   out_6599370070449602621[196] = 0;
   out_6599370070449602621[197] = 0;
   out_6599370070449602621[198] = 0;
   out_6599370070449602621[199] = 0;
   out_6599370070449602621[200] = 0;
   out_6599370070449602621[201] = 0;
   out_6599370070449602621[202] = 0;
   out_6599370070449602621[203] = 0;
   out_6599370070449602621[204] = 0;
   out_6599370070449602621[205] = 0;
   out_6599370070449602621[206] = 0;
   out_6599370070449602621[207] = 0;
   out_6599370070449602621[208] = 0;
   out_6599370070449602621[209] = 1;
   out_6599370070449602621[210] = 0;
   out_6599370070449602621[211] = 0;
   out_6599370070449602621[212] = 0;
   out_6599370070449602621[213] = 0;
   out_6599370070449602621[214] = 0;
   out_6599370070449602621[215] = 0;
   out_6599370070449602621[216] = 0;
   out_6599370070449602621[217] = 0;
   out_6599370070449602621[218] = 0;
   out_6599370070449602621[219] = 0;
   out_6599370070449602621[220] = 0;
   out_6599370070449602621[221] = 0;
   out_6599370070449602621[222] = 0;
   out_6599370070449602621[223] = 0;
   out_6599370070449602621[224] = 0;
   out_6599370070449602621[225] = 0;
   out_6599370070449602621[226] = 0;
   out_6599370070449602621[227] = 0;
   out_6599370070449602621[228] = 1;
   out_6599370070449602621[229] = 0;
   out_6599370070449602621[230] = 0;
   out_6599370070449602621[231] = 0;
   out_6599370070449602621[232] = 0;
   out_6599370070449602621[233] = 0;
   out_6599370070449602621[234] = 0;
   out_6599370070449602621[235] = 0;
   out_6599370070449602621[236] = 0;
   out_6599370070449602621[237] = 0;
   out_6599370070449602621[238] = 0;
   out_6599370070449602621[239] = 0;
   out_6599370070449602621[240] = 0;
   out_6599370070449602621[241] = 0;
   out_6599370070449602621[242] = 0;
   out_6599370070449602621[243] = 0;
   out_6599370070449602621[244] = 0;
   out_6599370070449602621[245] = 0;
   out_6599370070449602621[246] = 0;
   out_6599370070449602621[247] = 1;
   out_6599370070449602621[248] = 0;
   out_6599370070449602621[249] = 0;
   out_6599370070449602621[250] = 0;
   out_6599370070449602621[251] = 0;
   out_6599370070449602621[252] = 0;
   out_6599370070449602621[253] = 0;
   out_6599370070449602621[254] = 0;
   out_6599370070449602621[255] = 0;
   out_6599370070449602621[256] = 0;
   out_6599370070449602621[257] = 0;
   out_6599370070449602621[258] = 0;
   out_6599370070449602621[259] = 0;
   out_6599370070449602621[260] = 0;
   out_6599370070449602621[261] = 0;
   out_6599370070449602621[262] = 0;
   out_6599370070449602621[263] = 0;
   out_6599370070449602621[264] = 0;
   out_6599370070449602621[265] = 0;
   out_6599370070449602621[266] = 1;
   out_6599370070449602621[267] = 0;
   out_6599370070449602621[268] = 0;
   out_6599370070449602621[269] = 0;
   out_6599370070449602621[270] = 0;
   out_6599370070449602621[271] = 0;
   out_6599370070449602621[272] = 0;
   out_6599370070449602621[273] = 0;
   out_6599370070449602621[274] = 0;
   out_6599370070449602621[275] = 0;
   out_6599370070449602621[276] = 0;
   out_6599370070449602621[277] = 0;
   out_6599370070449602621[278] = 0;
   out_6599370070449602621[279] = 0;
   out_6599370070449602621[280] = 0;
   out_6599370070449602621[281] = 0;
   out_6599370070449602621[282] = 0;
   out_6599370070449602621[283] = 0;
   out_6599370070449602621[284] = 0;
   out_6599370070449602621[285] = 1;
   out_6599370070449602621[286] = 0;
   out_6599370070449602621[287] = 0;
   out_6599370070449602621[288] = 0;
   out_6599370070449602621[289] = 0;
   out_6599370070449602621[290] = 0;
   out_6599370070449602621[291] = 0;
   out_6599370070449602621[292] = 0;
   out_6599370070449602621[293] = 0;
   out_6599370070449602621[294] = 0;
   out_6599370070449602621[295] = 0;
   out_6599370070449602621[296] = 0;
   out_6599370070449602621[297] = 0;
   out_6599370070449602621[298] = 0;
   out_6599370070449602621[299] = 0;
   out_6599370070449602621[300] = 0;
   out_6599370070449602621[301] = 0;
   out_6599370070449602621[302] = 0;
   out_6599370070449602621[303] = 0;
   out_6599370070449602621[304] = 1;
   out_6599370070449602621[305] = 0;
   out_6599370070449602621[306] = 0;
   out_6599370070449602621[307] = 0;
   out_6599370070449602621[308] = 0;
   out_6599370070449602621[309] = 0;
   out_6599370070449602621[310] = 0;
   out_6599370070449602621[311] = 0;
   out_6599370070449602621[312] = 0;
   out_6599370070449602621[313] = 0;
   out_6599370070449602621[314] = 0;
   out_6599370070449602621[315] = 0;
   out_6599370070449602621[316] = 0;
   out_6599370070449602621[317] = 0;
   out_6599370070449602621[318] = 0;
   out_6599370070449602621[319] = 0;
   out_6599370070449602621[320] = 0;
   out_6599370070449602621[321] = 0;
   out_6599370070449602621[322] = 0;
   out_6599370070449602621[323] = 1;
}
void h_4(double *state, double *unused, double *out_1026954195093436293) {
   out_1026954195093436293[0] = state[6] + state[9];
   out_1026954195093436293[1] = state[7] + state[10];
   out_1026954195093436293[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3848307520625342162) {
   out_3848307520625342162[0] = 0;
   out_3848307520625342162[1] = 0;
   out_3848307520625342162[2] = 0;
   out_3848307520625342162[3] = 0;
   out_3848307520625342162[4] = 0;
   out_3848307520625342162[5] = 0;
   out_3848307520625342162[6] = 1;
   out_3848307520625342162[7] = 0;
   out_3848307520625342162[8] = 0;
   out_3848307520625342162[9] = 1;
   out_3848307520625342162[10] = 0;
   out_3848307520625342162[11] = 0;
   out_3848307520625342162[12] = 0;
   out_3848307520625342162[13] = 0;
   out_3848307520625342162[14] = 0;
   out_3848307520625342162[15] = 0;
   out_3848307520625342162[16] = 0;
   out_3848307520625342162[17] = 0;
   out_3848307520625342162[18] = 0;
   out_3848307520625342162[19] = 0;
   out_3848307520625342162[20] = 0;
   out_3848307520625342162[21] = 0;
   out_3848307520625342162[22] = 0;
   out_3848307520625342162[23] = 0;
   out_3848307520625342162[24] = 0;
   out_3848307520625342162[25] = 1;
   out_3848307520625342162[26] = 0;
   out_3848307520625342162[27] = 0;
   out_3848307520625342162[28] = 1;
   out_3848307520625342162[29] = 0;
   out_3848307520625342162[30] = 0;
   out_3848307520625342162[31] = 0;
   out_3848307520625342162[32] = 0;
   out_3848307520625342162[33] = 0;
   out_3848307520625342162[34] = 0;
   out_3848307520625342162[35] = 0;
   out_3848307520625342162[36] = 0;
   out_3848307520625342162[37] = 0;
   out_3848307520625342162[38] = 0;
   out_3848307520625342162[39] = 0;
   out_3848307520625342162[40] = 0;
   out_3848307520625342162[41] = 0;
   out_3848307520625342162[42] = 0;
   out_3848307520625342162[43] = 0;
   out_3848307520625342162[44] = 1;
   out_3848307520625342162[45] = 0;
   out_3848307520625342162[46] = 0;
   out_3848307520625342162[47] = 1;
   out_3848307520625342162[48] = 0;
   out_3848307520625342162[49] = 0;
   out_3848307520625342162[50] = 0;
   out_3848307520625342162[51] = 0;
   out_3848307520625342162[52] = 0;
   out_3848307520625342162[53] = 0;
}
void h_10(double *state, double *unused, double *out_6611596211326426316) {
   out_6611596211326426316[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6611596211326426316[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6611596211326426316[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5755249576477243564) {
   out_5755249576477243564[0] = 0;
   out_5755249576477243564[1] = 9.8100000000000005*cos(state[1]);
   out_5755249576477243564[2] = 0;
   out_5755249576477243564[3] = 0;
   out_5755249576477243564[4] = -state[8];
   out_5755249576477243564[5] = state[7];
   out_5755249576477243564[6] = 0;
   out_5755249576477243564[7] = state[5];
   out_5755249576477243564[8] = -state[4];
   out_5755249576477243564[9] = 0;
   out_5755249576477243564[10] = 0;
   out_5755249576477243564[11] = 0;
   out_5755249576477243564[12] = 1;
   out_5755249576477243564[13] = 0;
   out_5755249576477243564[14] = 0;
   out_5755249576477243564[15] = 1;
   out_5755249576477243564[16] = 0;
   out_5755249576477243564[17] = 0;
   out_5755249576477243564[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5755249576477243564[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5755249576477243564[20] = 0;
   out_5755249576477243564[21] = state[8];
   out_5755249576477243564[22] = 0;
   out_5755249576477243564[23] = -state[6];
   out_5755249576477243564[24] = -state[5];
   out_5755249576477243564[25] = 0;
   out_5755249576477243564[26] = state[3];
   out_5755249576477243564[27] = 0;
   out_5755249576477243564[28] = 0;
   out_5755249576477243564[29] = 0;
   out_5755249576477243564[30] = 0;
   out_5755249576477243564[31] = 1;
   out_5755249576477243564[32] = 0;
   out_5755249576477243564[33] = 0;
   out_5755249576477243564[34] = 1;
   out_5755249576477243564[35] = 0;
   out_5755249576477243564[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5755249576477243564[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5755249576477243564[38] = 0;
   out_5755249576477243564[39] = -state[7];
   out_5755249576477243564[40] = state[6];
   out_5755249576477243564[41] = 0;
   out_5755249576477243564[42] = state[4];
   out_5755249576477243564[43] = -state[3];
   out_5755249576477243564[44] = 0;
   out_5755249576477243564[45] = 0;
   out_5755249576477243564[46] = 0;
   out_5755249576477243564[47] = 0;
   out_5755249576477243564[48] = 0;
   out_5755249576477243564[49] = 0;
   out_5755249576477243564[50] = 1;
   out_5755249576477243564[51] = 0;
   out_5755249576477243564[52] = 0;
   out_5755249576477243564[53] = 1;
}
void h_13(double *state, double *unused, double *out_218234667872197902) {
   out_218234667872197902[0] = state[3];
   out_218234667872197902[1] = state[4];
   out_218234667872197902[2] = state[5];
}
void H_13(double *state, double *unused, double *out_636033695293009361) {
   out_636033695293009361[0] = 0;
   out_636033695293009361[1] = 0;
   out_636033695293009361[2] = 0;
   out_636033695293009361[3] = 1;
   out_636033695293009361[4] = 0;
   out_636033695293009361[5] = 0;
   out_636033695293009361[6] = 0;
   out_636033695293009361[7] = 0;
   out_636033695293009361[8] = 0;
   out_636033695293009361[9] = 0;
   out_636033695293009361[10] = 0;
   out_636033695293009361[11] = 0;
   out_636033695293009361[12] = 0;
   out_636033695293009361[13] = 0;
   out_636033695293009361[14] = 0;
   out_636033695293009361[15] = 0;
   out_636033695293009361[16] = 0;
   out_636033695293009361[17] = 0;
   out_636033695293009361[18] = 0;
   out_636033695293009361[19] = 0;
   out_636033695293009361[20] = 0;
   out_636033695293009361[21] = 0;
   out_636033695293009361[22] = 1;
   out_636033695293009361[23] = 0;
   out_636033695293009361[24] = 0;
   out_636033695293009361[25] = 0;
   out_636033695293009361[26] = 0;
   out_636033695293009361[27] = 0;
   out_636033695293009361[28] = 0;
   out_636033695293009361[29] = 0;
   out_636033695293009361[30] = 0;
   out_636033695293009361[31] = 0;
   out_636033695293009361[32] = 0;
   out_636033695293009361[33] = 0;
   out_636033695293009361[34] = 0;
   out_636033695293009361[35] = 0;
   out_636033695293009361[36] = 0;
   out_636033695293009361[37] = 0;
   out_636033695293009361[38] = 0;
   out_636033695293009361[39] = 0;
   out_636033695293009361[40] = 0;
   out_636033695293009361[41] = 1;
   out_636033695293009361[42] = 0;
   out_636033695293009361[43] = 0;
   out_636033695293009361[44] = 0;
   out_636033695293009361[45] = 0;
   out_636033695293009361[46] = 0;
   out_636033695293009361[47] = 0;
   out_636033695293009361[48] = 0;
   out_636033695293009361[49] = 0;
   out_636033695293009361[50] = 0;
   out_636033695293009361[51] = 0;
   out_636033695293009361[52] = 0;
   out_636033695293009361[53] = 0;
}
void h_14(double *state, double *unused, double *out_7359251233175886547) {
   out_7359251233175886547[0] = state[6];
   out_7359251233175886547[1] = state[7];
   out_7359251233175886547[2] = state[8];
}
void H_14(double *state, double *unused, double *out_114933335714142367) {
   out_114933335714142367[0] = 0;
   out_114933335714142367[1] = 0;
   out_114933335714142367[2] = 0;
   out_114933335714142367[3] = 0;
   out_114933335714142367[4] = 0;
   out_114933335714142367[5] = 0;
   out_114933335714142367[6] = 1;
   out_114933335714142367[7] = 0;
   out_114933335714142367[8] = 0;
   out_114933335714142367[9] = 0;
   out_114933335714142367[10] = 0;
   out_114933335714142367[11] = 0;
   out_114933335714142367[12] = 0;
   out_114933335714142367[13] = 0;
   out_114933335714142367[14] = 0;
   out_114933335714142367[15] = 0;
   out_114933335714142367[16] = 0;
   out_114933335714142367[17] = 0;
   out_114933335714142367[18] = 0;
   out_114933335714142367[19] = 0;
   out_114933335714142367[20] = 0;
   out_114933335714142367[21] = 0;
   out_114933335714142367[22] = 0;
   out_114933335714142367[23] = 0;
   out_114933335714142367[24] = 0;
   out_114933335714142367[25] = 1;
   out_114933335714142367[26] = 0;
   out_114933335714142367[27] = 0;
   out_114933335714142367[28] = 0;
   out_114933335714142367[29] = 0;
   out_114933335714142367[30] = 0;
   out_114933335714142367[31] = 0;
   out_114933335714142367[32] = 0;
   out_114933335714142367[33] = 0;
   out_114933335714142367[34] = 0;
   out_114933335714142367[35] = 0;
   out_114933335714142367[36] = 0;
   out_114933335714142367[37] = 0;
   out_114933335714142367[38] = 0;
   out_114933335714142367[39] = 0;
   out_114933335714142367[40] = 0;
   out_114933335714142367[41] = 0;
   out_114933335714142367[42] = 0;
   out_114933335714142367[43] = 0;
   out_114933335714142367[44] = 1;
   out_114933335714142367[45] = 0;
   out_114933335714142367[46] = 0;
   out_114933335714142367[47] = 0;
   out_114933335714142367[48] = 0;
   out_114933335714142367[49] = 0;
   out_114933335714142367[50] = 0;
   out_114933335714142367[51] = 0;
   out_114933335714142367[52] = 0;
   out_114933335714142367[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_2897896323809259494) {
  err_fun(nom_x, delta_x, out_2897896323809259494);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6584763988727841558) {
  inv_err_fun(nom_x, true_x, out_6584763988727841558);
}
void pose_H_mod_fun(double *state, double *out_5860240321001220316) {
  H_mod_fun(state, out_5860240321001220316);
}
void pose_f_fun(double *state, double dt, double *out_5165064222563725696) {
  f_fun(state,  dt, out_5165064222563725696);
}
void pose_F_fun(double *state, double dt, double *out_6599370070449602621) {
  F_fun(state,  dt, out_6599370070449602621);
}
void pose_h_4(double *state, double *unused, double *out_1026954195093436293) {
  h_4(state, unused, out_1026954195093436293);
}
void pose_H_4(double *state, double *unused, double *out_3848307520625342162) {
  H_4(state, unused, out_3848307520625342162);
}
void pose_h_10(double *state, double *unused, double *out_6611596211326426316) {
  h_10(state, unused, out_6611596211326426316);
}
void pose_H_10(double *state, double *unused, double *out_5755249576477243564) {
  H_10(state, unused, out_5755249576477243564);
}
void pose_h_13(double *state, double *unused, double *out_218234667872197902) {
  h_13(state, unused, out_218234667872197902);
}
void pose_H_13(double *state, double *unused, double *out_636033695293009361) {
  H_13(state, unused, out_636033695293009361);
}
void pose_h_14(double *state, double *unused, double *out_7359251233175886547) {
  h_14(state, unused, out_7359251233175886547);
}
void pose_H_14(double *state, double *unused, double *out_114933335714142367) {
  H_14(state, unused, out_114933335714142367);
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
