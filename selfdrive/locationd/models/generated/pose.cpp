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
void err_fun(double *nom_x, double *delta_x, double *out_867342344380239798) {
   out_867342344380239798[0] = delta_x[0] + nom_x[0];
   out_867342344380239798[1] = delta_x[1] + nom_x[1];
   out_867342344380239798[2] = delta_x[2] + nom_x[2];
   out_867342344380239798[3] = delta_x[3] + nom_x[3];
   out_867342344380239798[4] = delta_x[4] + nom_x[4];
   out_867342344380239798[5] = delta_x[5] + nom_x[5];
   out_867342344380239798[6] = delta_x[6] + nom_x[6];
   out_867342344380239798[7] = delta_x[7] + nom_x[7];
   out_867342344380239798[8] = delta_x[8] + nom_x[8];
   out_867342344380239798[9] = delta_x[9] + nom_x[9];
   out_867342344380239798[10] = delta_x[10] + nom_x[10];
   out_867342344380239798[11] = delta_x[11] + nom_x[11];
   out_867342344380239798[12] = delta_x[12] + nom_x[12];
   out_867342344380239798[13] = delta_x[13] + nom_x[13];
   out_867342344380239798[14] = delta_x[14] + nom_x[14];
   out_867342344380239798[15] = delta_x[15] + nom_x[15];
   out_867342344380239798[16] = delta_x[16] + nom_x[16];
   out_867342344380239798[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2946458972277190645) {
   out_2946458972277190645[0] = -nom_x[0] + true_x[0];
   out_2946458972277190645[1] = -nom_x[1] + true_x[1];
   out_2946458972277190645[2] = -nom_x[2] + true_x[2];
   out_2946458972277190645[3] = -nom_x[3] + true_x[3];
   out_2946458972277190645[4] = -nom_x[4] + true_x[4];
   out_2946458972277190645[5] = -nom_x[5] + true_x[5];
   out_2946458972277190645[6] = -nom_x[6] + true_x[6];
   out_2946458972277190645[7] = -nom_x[7] + true_x[7];
   out_2946458972277190645[8] = -nom_x[8] + true_x[8];
   out_2946458972277190645[9] = -nom_x[9] + true_x[9];
   out_2946458972277190645[10] = -nom_x[10] + true_x[10];
   out_2946458972277190645[11] = -nom_x[11] + true_x[11];
   out_2946458972277190645[12] = -nom_x[12] + true_x[12];
   out_2946458972277190645[13] = -nom_x[13] + true_x[13];
   out_2946458972277190645[14] = -nom_x[14] + true_x[14];
   out_2946458972277190645[15] = -nom_x[15] + true_x[15];
   out_2946458972277190645[16] = -nom_x[16] + true_x[16];
   out_2946458972277190645[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8034808007713849348) {
   out_8034808007713849348[0] = 1.0;
   out_8034808007713849348[1] = 0.0;
   out_8034808007713849348[2] = 0.0;
   out_8034808007713849348[3] = 0.0;
   out_8034808007713849348[4] = 0.0;
   out_8034808007713849348[5] = 0.0;
   out_8034808007713849348[6] = 0.0;
   out_8034808007713849348[7] = 0.0;
   out_8034808007713849348[8] = 0.0;
   out_8034808007713849348[9] = 0.0;
   out_8034808007713849348[10] = 0.0;
   out_8034808007713849348[11] = 0.0;
   out_8034808007713849348[12] = 0.0;
   out_8034808007713849348[13] = 0.0;
   out_8034808007713849348[14] = 0.0;
   out_8034808007713849348[15] = 0.0;
   out_8034808007713849348[16] = 0.0;
   out_8034808007713849348[17] = 0.0;
   out_8034808007713849348[18] = 0.0;
   out_8034808007713849348[19] = 1.0;
   out_8034808007713849348[20] = 0.0;
   out_8034808007713849348[21] = 0.0;
   out_8034808007713849348[22] = 0.0;
   out_8034808007713849348[23] = 0.0;
   out_8034808007713849348[24] = 0.0;
   out_8034808007713849348[25] = 0.0;
   out_8034808007713849348[26] = 0.0;
   out_8034808007713849348[27] = 0.0;
   out_8034808007713849348[28] = 0.0;
   out_8034808007713849348[29] = 0.0;
   out_8034808007713849348[30] = 0.0;
   out_8034808007713849348[31] = 0.0;
   out_8034808007713849348[32] = 0.0;
   out_8034808007713849348[33] = 0.0;
   out_8034808007713849348[34] = 0.0;
   out_8034808007713849348[35] = 0.0;
   out_8034808007713849348[36] = 0.0;
   out_8034808007713849348[37] = 0.0;
   out_8034808007713849348[38] = 1.0;
   out_8034808007713849348[39] = 0.0;
   out_8034808007713849348[40] = 0.0;
   out_8034808007713849348[41] = 0.0;
   out_8034808007713849348[42] = 0.0;
   out_8034808007713849348[43] = 0.0;
   out_8034808007713849348[44] = 0.0;
   out_8034808007713849348[45] = 0.0;
   out_8034808007713849348[46] = 0.0;
   out_8034808007713849348[47] = 0.0;
   out_8034808007713849348[48] = 0.0;
   out_8034808007713849348[49] = 0.0;
   out_8034808007713849348[50] = 0.0;
   out_8034808007713849348[51] = 0.0;
   out_8034808007713849348[52] = 0.0;
   out_8034808007713849348[53] = 0.0;
   out_8034808007713849348[54] = 0.0;
   out_8034808007713849348[55] = 0.0;
   out_8034808007713849348[56] = 0.0;
   out_8034808007713849348[57] = 1.0;
   out_8034808007713849348[58] = 0.0;
   out_8034808007713849348[59] = 0.0;
   out_8034808007713849348[60] = 0.0;
   out_8034808007713849348[61] = 0.0;
   out_8034808007713849348[62] = 0.0;
   out_8034808007713849348[63] = 0.0;
   out_8034808007713849348[64] = 0.0;
   out_8034808007713849348[65] = 0.0;
   out_8034808007713849348[66] = 0.0;
   out_8034808007713849348[67] = 0.0;
   out_8034808007713849348[68] = 0.0;
   out_8034808007713849348[69] = 0.0;
   out_8034808007713849348[70] = 0.0;
   out_8034808007713849348[71] = 0.0;
   out_8034808007713849348[72] = 0.0;
   out_8034808007713849348[73] = 0.0;
   out_8034808007713849348[74] = 0.0;
   out_8034808007713849348[75] = 0.0;
   out_8034808007713849348[76] = 1.0;
   out_8034808007713849348[77] = 0.0;
   out_8034808007713849348[78] = 0.0;
   out_8034808007713849348[79] = 0.0;
   out_8034808007713849348[80] = 0.0;
   out_8034808007713849348[81] = 0.0;
   out_8034808007713849348[82] = 0.0;
   out_8034808007713849348[83] = 0.0;
   out_8034808007713849348[84] = 0.0;
   out_8034808007713849348[85] = 0.0;
   out_8034808007713849348[86] = 0.0;
   out_8034808007713849348[87] = 0.0;
   out_8034808007713849348[88] = 0.0;
   out_8034808007713849348[89] = 0.0;
   out_8034808007713849348[90] = 0.0;
   out_8034808007713849348[91] = 0.0;
   out_8034808007713849348[92] = 0.0;
   out_8034808007713849348[93] = 0.0;
   out_8034808007713849348[94] = 0.0;
   out_8034808007713849348[95] = 1.0;
   out_8034808007713849348[96] = 0.0;
   out_8034808007713849348[97] = 0.0;
   out_8034808007713849348[98] = 0.0;
   out_8034808007713849348[99] = 0.0;
   out_8034808007713849348[100] = 0.0;
   out_8034808007713849348[101] = 0.0;
   out_8034808007713849348[102] = 0.0;
   out_8034808007713849348[103] = 0.0;
   out_8034808007713849348[104] = 0.0;
   out_8034808007713849348[105] = 0.0;
   out_8034808007713849348[106] = 0.0;
   out_8034808007713849348[107] = 0.0;
   out_8034808007713849348[108] = 0.0;
   out_8034808007713849348[109] = 0.0;
   out_8034808007713849348[110] = 0.0;
   out_8034808007713849348[111] = 0.0;
   out_8034808007713849348[112] = 0.0;
   out_8034808007713849348[113] = 0.0;
   out_8034808007713849348[114] = 1.0;
   out_8034808007713849348[115] = 0.0;
   out_8034808007713849348[116] = 0.0;
   out_8034808007713849348[117] = 0.0;
   out_8034808007713849348[118] = 0.0;
   out_8034808007713849348[119] = 0.0;
   out_8034808007713849348[120] = 0.0;
   out_8034808007713849348[121] = 0.0;
   out_8034808007713849348[122] = 0.0;
   out_8034808007713849348[123] = 0.0;
   out_8034808007713849348[124] = 0.0;
   out_8034808007713849348[125] = 0.0;
   out_8034808007713849348[126] = 0.0;
   out_8034808007713849348[127] = 0.0;
   out_8034808007713849348[128] = 0.0;
   out_8034808007713849348[129] = 0.0;
   out_8034808007713849348[130] = 0.0;
   out_8034808007713849348[131] = 0.0;
   out_8034808007713849348[132] = 0.0;
   out_8034808007713849348[133] = 1.0;
   out_8034808007713849348[134] = 0.0;
   out_8034808007713849348[135] = 0.0;
   out_8034808007713849348[136] = 0.0;
   out_8034808007713849348[137] = 0.0;
   out_8034808007713849348[138] = 0.0;
   out_8034808007713849348[139] = 0.0;
   out_8034808007713849348[140] = 0.0;
   out_8034808007713849348[141] = 0.0;
   out_8034808007713849348[142] = 0.0;
   out_8034808007713849348[143] = 0.0;
   out_8034808007713849348[144] = 0.0;
   out_8034808007713849348[145] = 0.0;
   out_8034808007713849348[146] = 0.0;
   out_8034808007713849348[147] = 0.0;
   out_8034808007713849348[148] = 0.0;
   out_8034808007713849348[149] = 0.0;
   out_8034808007713849348[150] = 0.0;
   out_8034808007713849348[151] = 0.0;
   out_8034808007713849348[152] = 1.0;
   out_8034808007713849348[153] = 0.0;
   out_8034808007713849348[154] = 0.0;
   out_8034808007713849348[155] = 0.0;
   out_8034808007713849348[156] = 0.0;
   out_8034808007713849348[157] = 0.0;
   out_8034808007713849348[158] = 0.0;
   out_8034808007713849348[159] = 0.0;
   out_8034808007713849348[160] = 0.0;
   out_8034808007713849348[161] = 0.0;
   out_8034808007713849348[162] = 0.0;
   out_8034808007713849348[163] = 0.0;
   out_8034808007713849348[164] = 0.0;
   out_8034808007713849348[165] = 0.0;
   out_8034808007713849348[166] = 0.0;
   out_8034808007713849348[167] = 0.0;
   out_8034808007713849348[168] = 0.0;
   out_8034808007713849348[169] = 0.0;
   out_8034808007713849348[170] = 0.0;
   out_8034808007713849348[171] = 1.0;
   out_8034808007713849348[172] = 0.0;
   out_8034808007713849348[173] = 0.0;
   out_8034808007713849348[174] = 0.0;
   out_8034808007713849348[175] = 0.0;
   out_8034808007713849348[176] = 0.0;
   out_8034808007713849348[177] = 0.0;
   out_8034808007713849348[178] = 0.0;
   out_8034808007713849348[179] = 0.0;
   out_8034808007713849348[180] = 0.0;
   out_8034808007713849348[181] = 0.0;
   out_8034808007713849348[182] = 0.0;
   out_8034808007713849348[183] = 0.0;
   out_8034808007713849348[184] = 0.0;
   out_8034808007713849348[185] = 0.0;
   out_8034808007713849348[186] = 0.0;
   out_8034808007713849348[187] = 0.0;
   out_8034808007713849348[188] = 0.0;
   out_8034808007713849348[189] = 0.0;
   out_8034808007713849348[190] = 1.0;
   out_8034808007713849348[191] = 0.0;
   out_8034808007713849348[192] = 0.0;
   out_8034808007713849348[193] = 0.0;
   out_8034808007713849348[194] = 0.0;
   out_8034808007713849348[195] = 0.0;
   out_8034808007713849348[196] = 0.0;
   out_8034808007713849348[197] = 0.0;
   out_8034808007713849348[198] = 0.0;
   out_8034808007713849348[199] = 0.0;
   out_8034808007713849348[200] = 0.0;
   out_8034808007713849348[201] = 0.0;
   out_8034808007713849348[202] = 0.0;
   out_8034808007713849348[203] = 0.0;
   out_8034808007713849348[204] = 0.0;
   out_8034808007713849348[205] = 0.0;
   out_8034808007713849348[206] = 0.0;
   out_8034808007713849348[207] = 0.0;
   out_8034808007713849348[208] = 0.0;
   out_8034808007713849348[209] = 1.0;
   out_8034808007713849348[210] = 0.0;
   out_8034808007713849348[211] = 0.0;
   out_8034808007713849348[212] = 0.0;
   out_8034808007713849348[213] = 0.0;
   out_8034808007713849348[214] = 0.0;
   out_8034808007713849348[215] = 0.0;
   out_8034808007713849348[216] = 0.0;
   out_8034808007713849348[217] = 0.0;
   out_8034808007713849348[218] = 0.0;
   out_8034808007713849348[219] = 0.0;
   out_8034808007713849348[220] = 0.0;
   out_8034808007713849348[221] = 0.0;
   out_8034808007713849348[222] = 0.0;
   out_8034808007713849348[223] = 0.0;
   out_8034808007713849348[224] = 0.0;
   out_8034808007713849348[225] = 0.0;
   out_8034808007713849348[226] = 0.0;
   out_8034808007713849348[227] = 0.0;
   out_8034808007713849348[228] = 1.0;
   out_8034808007713849348[229] = 0.0;
   out_8034808007713849348[230] = 0.0;
   out_8034808007713849348[231] = 0.0;
   out_8034808007713849348[232] = 0.0;
   out_8034808007713849348[233] = 0.0;
   out_8034808007713849348[234] = 0.0;
   out_8034808007713849348[235] = 0.0;
   out_8034808007713849348[236] = 0.0;
   out_8034808007713849348[237] = 0.0;
   out_8034808007713849348[238] = 0.0;
   out_8034808007713849348[239] = 0.0;
   out_8034808007713849348[240] = 0.0;
   out_8034808007713849348[241] = 0.0;
   out_8034808007713849348[242] = 0.0;
   out_8034808007713849348[243] = 0.0;
   out_8034808007713849348[244] = 0.0;
   out_8034808007713849348[245] = 0.0;
   out_8034808007713849348[246] = 0.0;
   out_8034808007713849348[247] = 1.0;
   out_8034808007713849348[248] = 0.0;
   out_8034808007713849348[249] = 0.0;
   out_8034808007713849348[250] = 0.0;
   out_8034808007713849348[251] = 0.0;
   out_8034808007713849348[252] = 0.0;
   out_8034808007713849348[253] = 0.0;
   out_8034808007713849348[254] = 0.0;
   out_8034808007713849348[255] = 0.0;
   out_8034808007713849348[256] = 0.0;
   out_8034808007713849348[257] = 0.0;
   out_8034808007713849348[258] = 0.0;
   out_8034808007713849348[259] = 0.0;
   out_8034808007713849348[260] = 0.0;
   out_8034808007713849348[261] = 0.0;
   out_8034808007713849348[262] = 0.0;
   out_8034808007713849348[263] = 0.0;
   out_8034808007713849348[264] = 0.0;
   out_8034808007713849348[265] = 0.0;
   out_8034808007713849348[266] = 1.0;
   out_8034808007713849348[267] = 0.0;
   out_8034808007713849348[268] = 0.0;
   out_8034808007713849348[269] = 0.0;
   out_8034808007713849348[270] = 0.0;
   out_8034808007713849348[271] = 0.0;
   out_8034808007713849348[272] = 0.0;
   out_8034808007713849348[273] = 0.0;
   out_8034808007713849348[274] = 0.0;
   out_8034808007713849348[275] = 0.0;
   out_8034808007713849348[276] = 0.0;
   out_8034808007713849348[277] = 0.0;
   out_8034808007713849348[278] = 0.0;
   out_8034808007713849348[279] = 0.0;
   out_8034808007713849348[280] = 0.0;
   out_8034808007713849348[281] = 0.0;
   out_8034808007713849348[282] = 0.0;
   out_8034808007713849348[283] = 0.0;
   out_8034808007713849348[284] = 0.0;
   out_8034808007713849348[285] = 1.0;
   out_8034808007713849348[286] = 0.0;
   out_8034808007713849348[287] = 0.0;
   out_8034808007713849348[288] = 0.0;
   out_8034808007713849348[289] = 0.0;
   out_8034808007713849348[290] = 0.0;
   out_8034808007713849348[291] = 0.0;
   out_8034808007713849348[292] = 0.0;
   out_8034808007713849348[293] = 0.0;
   out_8034808007713849348[294] = 0.0;
   out_8034808007713849348[295] = 0.0;
   out_8034808007713849348[296] = 0.0;
   out_8034808007713849348[297] = 0.0;
   out_8034808007713849348[298] = 0.0;
   out_8034808007713849348[299] = 0.0;
   out_8034808007713849348[300] = 0.0;
   out_8034808007713849348[301] = 0.0;
   out_8034808007713849348[302] = 0.0;
   out_8034808007713849348[303] = 0.0;
   out_8034808007713849348[304] = 1.0;
   out_8034808007713849348[305] = 0.0;
   out_8034808007713849348[306] = 0.0;
   out_8034808007713849348[307] = 0.0;
   out_8034808007713849348[308] = 0.0;
   out_8034808007713849348[309] = 0.0;
   out_8034808007713849348[310] = 0.0;
   out_8034808007713849348[311] = 0.0;
   out_8034808007713849348[312] = 0.0;
   out_8034808007713849348[313] = 0.0;
   out_8034808007713849348[314] = 0.0;
   out_8034808007713849348[315] = 0.0;
   out_8034808007713849348[316] = 0.0;
   out_8034808007713849348[317] = 0.0;
   out_8034808007713849348[318] = 0.0;
   out_8034808007713849348[319] = 0.0;
   out_8034808007713849348[320] = 0.0;
   out_8034808007713849348[321] = 0.0;
   out_8034808007713849348[322] = 0.0;
   out_8034808007713849348[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5448742405462655453) {
   out_5448742405462655453[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5448742405462655453[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5448742405462655453[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5448742405462655453[3] = dt*state[12] + state[3];
   out_5448742405462655453[4] = dt*state[13] + state[4];
   out_5448742405462655453[5] = dt*state[14] + state[5];
   out_5448742405462655453[6] = state[6];
   out_5448742405462655453[7] = state[7];
   out_5448742405462655453[8] = state[8];
   out_5448742405462655453[9] = state[9];
   out_5448742405462655453[10] = state[10];
   out_5448742405462655453[11] = state[11];
   out_5448742405462655453[12] = state[12];
   out_5448742405462655453[13] = state[13];
   out_5448742405462655453[14] = state[14];
   out_5448742405462655453[15] = state[15];
   out_5448742405462655453[16] = state[16];
   out_5448742405462655453[17] = state[17];
}
void F_fun(double *state, double dt, double *out_582733379073092242) {
   out_582733379073092242[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_582733379073092242[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_582733379073092242[2] = 0;
   out_582733379073092242[3] = 0;
   out_582733379073092242[4] = 0;
   out_582733379073092242[5] = 0;
   out_582733379073092242[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_582733379073092242[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_582733379073092242[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_582733379073092242[9] = 0;
   out_582733379073092242[10] = 0;
   out_582733379073092242[11] = 0;
   out_582733379073092242[12] = 0;
   out_582733379073092242[13] = 0;
   out_582733379073092242[14] = 0;
   out_582733379073092242[15] = 0;
   out_582733379073092242[16] = 0;
   out_582733379073092242[17] = 0;
   out_582733379073092242[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_582733379073092242[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_582733379073092242[20] = 0;
   out_582733379073092242[21] = 0;
   out_582733379073092242[22] = 0;
   out_582733379073092242[23] = 0;
   out_582733379073092242[24] = 0;
   out_582733379073092242[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_582733379073092242[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_582733379073092242[27] = 0;
   out_582733379073092242[28] = 0;
   out_582733379073092242[29] = 0;
   out_582733379073092242[30] = 0;
   out_582733379073092242[31] = 0;
   out_582733379073092242[32] = 0;
   out_582733379073092242[33] = 0;
   out_582733379073092242[34] = 0;
   out_582733379073092242[35] = 0;
   out_582733379073092242[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_582733379073092242[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_582733379073092242[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_582733379073092242[39] = 0;
   out_582733379073092242[40] = 0;
   out_582733379073092242[41] = 0;
   out_582733379073092242[42] = 0;
   out_582733379073092242[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_582733379073092242[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_582733379073092242[45] = 0;
   out_582733379073092242[46] = 0;
   out_582733379073092242[47] = 0;
   out_582733379073092242[48] = 0;
   out_582733379073092242[49] = 0;
   out_582733379073092242[50] = 0;
   out_582733379073092242[51] = 0;
   out_582733379073092242[52] = 0;
   out_582733379073092242[53] = 0;
   out_582733379073092242[54] = 0;
   out_582733379073092242[55] = 0;
   out_582733379073092242[56] = 0;
   out_582733379073092242[57] = 1;
   out_582733379073092242[58] = 0;
   out_582733379073092242[59] = 0;
   out_582733379073092242[60] = 0;
   out_582733379073092242[61] = 0;
   out_582733379073092242[62] = 0;
   out_582733379073092242[63] = 0;
   out_582733379073092242[64] = 0;
   out_582733379073092242[65] = 0;
   out_582733379073092242[66] = dt;
   out_582733379073092242[67] = 0;
   out_582733379073092242[68] = 0;
   out_582733379073092242[69] = 0;
   out_582733379073092242[70] = 0;
   out_582733379073092242[71] = 0;
   out_582733379073092242[72] = 0;
   out_582733379073092242[73] = 0;
   out_582733379073092242[74] = 0;
   out_582733379073092242[75] = 0;
   out_582733379073092242[76] = 1;
   out_582733379073092242[77] = 0;
   out_582733379073092242[78] = 0;
   out_582733379073092242[79] = 0;
   out_582733379073092242[80] = 0;
   out_582733379073092242[81] = 0;
   out_582733379073092242[82] = 0;
   out_582733379073092242[83] = 0;
   out_582733379073092242[84] = 0;
   out_582733379073092242[85] = dt;
   out_582733379073092242[86] = 0;
   out_582733379073092242[87] = 0;
   out_582733379073092242[88] = 0;
   out_582733379073092242[89] = 0;
   out_582733379073092242[90] = 0;
   out_582733379073092242[91] = 0;
   out_582733379073092242[92] = 0;
   out_582733379073092242[93] = 0;
   out_582733379073092242[94] = 0;
   out_582733379073092242[95] = 1;
   out_582733379073092242[96] = 0;
   out_582733379073092242[97] = 0;
   out_582733379073092242[98] = 0;
   out_582733379073092242[99] = 0;
   out_582733379073092242[100] = 0;
   out_582733379073092242[101] = 0;
   out_582733379073092242[102] = 0;
   out_582733379073092242[103] = 0;
   out_582733379073092242[104] = dt;
   out_582733379073092242[105] = 0;
   out_582733379073092242[106] = 0;
   out_582733379073092242[107] = 0;
   out_582733379073092242[108] = 0;
   out_582733379073092242[109] = 0;
   out_582733379073092242[110] = 0;
   out_582733379073092242[111] = 0;
   out_582733379073092242[112] = 0;
   out_582733379073092242[113] = 0;
   out_582733379073092242[114] = 1;
   out_582733379073092242[115] = 0;
   out_582733379073092242[116] = 0;
   out_582733379073092242[117] = 0;
   out_582733379073092242[118] = 0;
   out_582733379073092242[119] = 0;
   out_582733379073092242[120] = 0;
   out_582733379073092242[121] = 0;
   out_582733379073092242[122] = 0;
   out_582733379073092242[123] = 0;
   out_582733379073092242[124] = 0;
   out_582733379073092242[125] = 0;
   out_582733379073092242[126] = 0;
   out_582733379073092242[127] = 0;
   out_582733379073092242[128] = 0;
   out_582733379073092242[129] = 0;
   out_582733379073092242[130] = 0;
   out_582733379073092242[131] = 0;
   out_582733379073092242[132] = 0;
   out_582733379073092242[133] = 1;
   out_582733379073092242[134] = 0;
   out_582733379073092242[135] = 0;
   out_582733379073092242[136] = 0;
   out_582733379073092242[137] = 0;
   out_582733379073092242[138] = 0;
   out_582733379073092242[139] = 0;
   out_582733379073092242[140] = 0;
   out_582733379073092242[141] = 0;
   out_582733379073092242[142] = 0;
   out_582733379073092242[143] = 0;
   out_582733379073092242[144] = 0;
   out_582733379073092242[145] = 0;
   out_582733379073092242[146] = 0;
   out_582733379073092242[147] = 0;
   out_582733379073092242[148] = 0;
   out_582733379073092242[149] = 0;
   out_582733379073092242[150] = 0;
   out_582733379073092242[151] = 0;
   out_582733379073092242[152] = 1;
   out_582733379073092242[153] = 0;
   out_582733379073092242[154] = 0;
   out_582733379073092242[155] = 0;
   out_582733379073092242[156] = 0;
   out_582733379073092242[157] = 0;
   out_582733379073092242[158] = 0;
   out_582733379073092242[159] = 0;
   out_582733379073092242[160] = 0;
   out_582733379073092242[161] = 0;
   out_582733379073092242[162] = 0;
   out_582733379073092242[163] = 0;
   out_582733379073092242[164] = 0;
   out_582733379073092242[165] = 0;
   out_582733379073092242[166] = 0;
   out_582733379073092242[167] = 0;
   out_582733379073092242[168] = 0;
   out_582733379073092242[169] = 0;
   out_582733379073092242[170] = 0;
   out_582733379073092242[171] = 1;
   out_582733379073092242[172] = 0;
   out_582733379073092242[173] = 0;
   out_582733379073092242[174] = 0;
   out_582733379073092242[175] = 0;
   out_582733379073092242[176] = 0;
   out_582733379073092242[177] = 0;
   out_582733379073092242[178] = 0;
   out_582733379073092242[179] = 0;
   out_582733379073092242[180] = 0;
   out_582733379073092242[181] = 0;
   out_582733379073092242[182] = 0;
   out_582733379073092242[183] = 0;
   out_582733379073092242[184] = 0;
   out_582733379073092242[185] = 0;
   out_582733379073092242[186] = 0;
   out_582733379073092242[187] = 0;
   out_582733379073092242[188] = 0;
   out_582733379073092242[189] = 0;
   out_582733379073092242[190] = 1;
   out_582733379073092242[191] = 0;
   out_582733379073092242[192] = 0;
   out_582733379073092242[193] = 0;
   out_582733379073092242[194] = 0;
   out_582733379073092242[195] = 0;
   out_582733379073092242[196] = 0;
   out_582733379073092242[197] = 0;
   out_582733379073092242[198] = 0;
   out_582733379073092242[199] = 0;
   out_582733379073092242[200] = 0;
   out_582733379073092242[201] = 0;
   out_582733379073092242[202] = 0;
   out_582733379073092242[203] = 0;
   out_582733379073092242[204] = 0;
   out_582733379073092242[205] = 0;
   out_582733379073092242[206] = 0;
   out_582733379073092242[207] = 0;
   out_582733379073092242[208] = 0;
   out_582733379073092242[209] = 1;
   out_582733379073092242[210] = 0;
   out_582733379073092242[211] = 0;
   out_582733379073092242[212] = 0;
   out_582733379073092242[213] = 0;
   out_582733379073092242[214] = 0;
   out_582733379073092242[215] = 0;
   out_582733379073092242[216] = 0;
   out_582733379073092242[217] = 0;
   out_582733379073092242[218] = 0;
   out_582733379073092242[219] = 0;
   out_582733379073092242[220] = 0;
   out_582733379073092242[221] = 0;
   out_582733379073092242[222] = 0;
   out_582733379073092242[223] = 0;
   out_582733379073092242[224] = 0;
   out_582733379073092242[225] = 0;
   out_582733379073092242[226] = 0;
   out_582733379073092242[227] = 0;
   out_582733379073092242[228] = 1;
   out_582733379073092242[229] = 0;
   out_582733379073092242[230] = 0;
   out_582733379073092242[231] = 0;
   out_582733379073092242[232] = 0;
   out_582733379073092242[233] = 0;
   out_582733379073092242[234] = 0;
   out_582733379073092242[235] = 0;
   out_582733379073092242[236] = 0;
   out_582733379073092242[237] = 0;
   out_582733379073092242[238] = 0;
   out_582733379073092242[239] = 0;
   out_582733379073092242[240] = 0;
   out_582733379073092242[241] = 0;
   out_582733379073092242[242] = 0;
   out_582733379073092242[243] = 0;
   out_582733379073092242[244] = 0;
   out_582733379073092242[245] = 0;
   out_582733379073092242[246] = 0;
   out_582733379073092242[247] = 1;
   out_582733379073092242[248] = 0;
   out_582733379073092242[249] = 0;
   out_582733379073092242[250] = 0;
   out_582733379073092242[251] = 0;
   out_582733379073092242[252] = 0;
   out_582733379073092242[253] = 0;
   out_582733379073092242[254] = 0;
   out_582733379073092242[255] = 0;
   out_582733379073092242[256] = 0;
   out_582733379073092242[257] = 0;
   out_582733379073092242[258] = 0;
   out_582733379073092242[259] = 0;
   out_582733379073092242[260] = 0;
   out_582733379073092242[261] = 0;
   out_582733379073092242[262] = 0;
   out_582733379073092242[263] = 0;
   out_582733379073092242[264] = 0;
   out_582733379073092242[265] = 0;
   out_582733379073092242[266] = 1;
   out_582733379073092242[267] = 0;
   out_582733379073092242[268] = 0;
   out_582733379073092242[269] = 0;
   out_582733379073092242[270] = 0;
   out_582733379073092242[271] = 0;
   out_582733379073092242[272] = 0;
   out_582733379073092242[273] = 0;
   out_582733379073092242[274] = 0;
   out_582733379073092242[275] = 0;
   out_582733379073092242[276] = 0;
   out_582733379073092242[277] = 0;
   out_582733379073092242[278] = 0;
   out_582733379073092242[279] = 0;
   out_582733379073092242[280] = 0;
   out_582733379073092242[281] = 0;
   out_582733379073092242[282] = 0;
   out_582733379073092242[283] = 0;
   out_582733379073092242[284] = 0;
   out_582733379073092242[285] = 1;
   out_582733379073092242[286] = 0;
   out_582733379073092242[287] = 0;
   out_582733379073092242[288] = 0;
   out_582733379073092242[289] = 0;
   out_582733379073092242[290] = 0;
   out_582733379073092242[291] = 0;
   out_582733379073092242[292] = 0;
   out_582733379073092242[293] = 0;
   out_582733379073092242[294] = 0;
   out_582733379073092242[295] = 0;
   out_582733379073092242[296] = 0;
   out_582733379073092242[297] = 0;
   out_582733379073092242[298] = 0;
   out_582733379073092242[299] = 0;
   out_582733379073092242[300] = 0;
   out_582733379073092242[301] = 0;
   out_582733379073092242[302] = 0;
   out_582733379073092242[303] = 0;
   out_582733379073092242[304] = 1;
   out_582733379073092242[305] = 0;
   out_582733379073092242[306] = 0;
   out_582733379073092242[307] = 0;
   out_582733379073092242[308] = 0;
   out_582733379073092242[309] = 0;
   out_582733379073092242[310] = 0;
   out_582733379073092242[311] = 0;
   out_582733379073092242[312] = 0;
   out_582733379073092242[313] = 0;
   out_582733379073092242[314] = 0;
   out_582733379073092242[315] = 0;
   out_582733379073092242[316] = 0;
   out_582733379073092242[317] = 0;
   out_582733379073092242[318] = 0;
   out_582733379073092242[319] = 0;
   out_582733379073092242[320] = 0;
   out_582733379073092242[321] = 0;
   out_582733379073092242[322] = 0;
   out_582733379073092242[323] = 1;
}
void h_4(double *state, double *unused, double *out_959952002277923346) {
   out_959952002277923346[0] = state[6] + state[9];
   out_959952002277923346[1] = state[7] + state[10];
   out_959952002277923346[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1467574399937880926) {
   out_1467574399937880926[0] = 0;
   out_1467574399937880926[1] = 0;
   out_1467574399937880926[2] = 0;
   out_1467574399937880926[3] = 0;
   out_1467574399937880926[4] = 0;
   out_1467574399937880926[5] = 0;
   out_1467574399937880926[6] = 1;
   out_1467574399937880926[7] = 0;
   out_1467574399937880926[8] = 0;
   out_1467574399937880926[9] = 1;
   out_1467574399937880926[10] = 0;
   out_1467574399937880926[11] = 0;
   out_1467574399937880926[12] = 0;
   out_1467574399937880926[13] = 0;
   out_1467574399937880926[14] = 0;
   out_1467574399937880926[15] = 0;
   out_1467574399937880926[16] = 0;
   out_1467574399937880926[17] = 0;
   out_1467574399937880926[18] = 0;
   out_1467574399937880926[19] = 0;
   out_1467574399937880926[20] = 0;
   out_1467574399937880926[21] = 0;
   out_1467574399937880926[22] = 0;
   out_1467574399937880926[23] = 0;
   out_1467574399937880926[24] = 0;
   out_1467574399937880926[25] = 1;
   out_1467574399937880926[26] = 0;
   out_1467574399937880926[27] = 0;
   out_1467574399937880926[28] = 1;
   out_1467574399937880926[29] = 0;
   out_1467574399937880926[30] = 0;
   out_1467574399937880926[31] = 0;
   out_1467574399937880926[32] = 0;
   out_1467574399937880926[33] = 0;
   out_1467574399937880926[34] = 0;
   out_1467574399937880926[35] = 0;
   out_1467574399937880926[36] = 0;
   out_1467574399937880926[37] = 0;
   out_1467574399937880926[38] = 0;
   out_1467574399937880926[39] = 0;
   out_1467574399937880926[40] = 0;
   out_1467574399937880926[41] = 0;
   out_1467574399937880926[42] = 0;
   out_1467574399937880926[43] = 0;
   out_1467574399937880926[44] = 1;
   out_1467574399937880926[45] = 0;
   out_1467574399937880926[46] = 0;
   out_1467574399937880926[47] = 1;
   out_1467574399937880926[48] = 0;
   out_1467574399937880926[49] = 0;
   out_1467574399937880926[50] = 0;
   out_1467574399937880926[51] = 0;
   out_1467574399937880926[52] = 0;
   out_1467574399937880926[53] = 0;
}
void h_10(double *state, double *unused, double *out_315403293584823803) {
   out_315403293584823803[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_315403293584823803[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_315403293584823803[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2334763542090568144) {
   out_2334763542090568144[0] = 0;
   out_2334763542090568144[1] = 9.8100000000000005*cos(state[1]);
   out_2334763542090568144[2] = 0;
   out_2334763542090568144[3] = 0;
   out_2334763542090568144[4] = -state[8];
   out_2334763542090568144[5] = state[7];
   out_2334763542090568144[6] = 0;
   out_2334763542090568144[7] = state[5];
   out_2334763542090568144[8] = -state[4];
   out_2334763542090568144[9] = 0;
   out_2334763542090568144[10] = 0;
   out_2334763542090568144[11] = 0;
   out_2334763542090568144[12] = 1;
   out_2334763542090568144[13] = 0;
   out_2334763542090568144[14] = 0;
   out_2334763542090568144[15] = 1;
   out_2334763542090568144[16] = 0;
   out_2334763542090568144[17] = 0;
   out_2334763542090568144[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2334763542090568144[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2334763542090568144[20] = 0;
   out_2334763542090568144[21] = state[8];
   out_2334763542090568144[22] = 0;
   out_2334763542090568144[23] = -state[6];
   out_2334763542090568144[24] = -state[5];
   out_2334763542090568144[25] = 0;
   out_2334763542090568144[26] = state[3];
   out_2334763542090568144[27] = 0;
   out_2334763542090568144[28] = 0;
   out_2334763542090568144[29] = 0;
   out_2334763542090568144[30] = 0;
   out_2334763542090568144[31] = 1;
   out_2334763542090568144[32] = 0;
   out_2334763542090568144[33] = 0;
   out_2334763542090568144[34] = 1;
   out_2334763542090568144[35] = 0;
   out_2334763542090568144[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2334763542090568144[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2334763542090568144[38] = 0;
   out_2334763542090568144[39] = -state[7];
   out_2334763542090568144[40] = state[6];
   out_2334763542090568144[41] = 0;
   out_2334763542090568144[42] = state[4];
   out_2334763542090568144[43] = -state[3];
   out_2334763542090568144[44] = 0;
   out_2334763542090568144[45] = 0;
   out_2334763542090568144[46] = 0;
   out_2334763542090568144[47] = 0;
   out_2334763542090568144[48] = 0;
   out_2334763542090568144[49] = 0;
   out_2334763542090568144[50] = 1;
   out_2334763542090568144[51] = 0;
   out_2334763542090568144[52] = 0;
   out_2334763542090568144[53] = 1;
}
void h_13(double *state, double *unused, double *out_5013407308002664142) {
   out_5013407308002664142[0] = state[3];
   out_5013407308002664142[1] = state[4];
   out_5013407308002664142[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4679848225270213727) {
   out_4679848225270213727[0] = 0;
   out_4679848225270213727[1] = 0;
   out_4679848225270213727[2] = 0;
   out_4679848225270213727[3] = 1;
   out_4679848225270213727[4] = 0;
   out_4679848225270213727[5] = 0;
   out_4679848225270213727[6] = 0;
   out_4679848225270213727[7] = 0;
   out_4679848225270213727[8] = 0;
   out_4679848225270213727[9] = 0;
   out_4679848225270213727[10] = 0;
   out_4679848225270213727[11] = 0;
   out_4679848225270213727[12] = 0;
   out_4679848225270213727[13] = 0;
   out_4679848225270213727[14] = 0;
   out_4679848225270213727[15] = 0;
   out_4679848225270213727[16] = 0;
   out_4679848225270213727[17] = 0;
   out_4679848225270213727[18] = 0;
   out_4679848225270213727[19] = 0;
   out_4679848225270213727[20] = 0;
   out_4679848225270213727[21] = 0;
   out_4679848225270213727[22] = 1;
   out_4679848225270213727[23] = 0;
   out_4679848225270213727[24] = 0;
   out_4679848225270213727[25] = 0;
   out_4679848225270213727[26] = 0;
   out_4679848225270213727[27] = 0;
   out_4679848225270213727[28] = 0;
   out_4679848225270213727[29] = 0;
   out_4679848225270213727[30] = 0;
   out_4679848225270213727[31] = 0;
   out_4679848225270213727[32] = 0;
   out_4679848225270213727[33] = 0;
   out_4679848225270213727[34] = 0;
   out_4679848225270213727[35] = 0;
   out_4679848225270213727[36] = 0;
   out_4679848225270213727[37] = 0;
   out_4679848225270213727[38] = 0;
   out_4679848225270213727[39] = 0;
   out_4679848225270213727[40] = 0;
   out_4679848225270213727[41] = 1;
   out_4679848225270213727[42] = 0;
   out_4679848225270213727[43] = 0;
   out_4679848225270213727[44] = 0;
   out_4679848225270213727[45] = 0;
   out_4679848225270213727[46] = 0;
   out_4679848225270213727[47] = 0;
   out_4679848225270213727[48] = 0;
   out_4679848225270213727[49] = 0;
   out_4679848225270213727[50] = 0;
   out_4679848225270213727[51] = 0;
   out_4679848225270213727[52] = 0;
   out_4679848225270213727[53] = 0;
}
void h_14(double *state, double *unused, double *out_6338305732819674146) {
   out_6338305732819674146[0] = state[6];
   out_6338305732819674146[1] = state[7];
   out_6338305732819674146[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1615214032357491370) {
   out_1615214032357491370[0] = 0;
   out_1615214032357491370[1] = 0;
   out_1615214032357491370[2] = 0;
   out_1615214032357491370[3] = 0;
   out_1615214032357491370[4] = 0;
   out_1615214032357491370[5] = 0;
   out_1615214032357491370[6] = 1;
   out_1615214032357491370[7] = 0;
   out_1615214032357491370[8] = 0;
   out_1615214032357491370[9] = 0;
   out_1615214032357491370[10] = 0;
   out_1615214032357491370[11] = 0;
   out_1615214032357491370[12] = 0;
   out_1615214032357491370[13] = 0;
   out_1615214032357491370[14] = 0;
   out_1615214032357491370[15] = 0;
   out_1615214032357491370[16] = 0;
   out_1615214032357491370[17] = 0;
   out_1615214032357491370[18] = 0;
   out_1615214032357491370[19] = 0;
   out_1615214032357491370[20] = 0;
   out_1615214032357491370[21] = 0;
   out_1615214032357491370[22] = 0;
   out_1615214032357491370[23] = 0;
   out_1615214032357491370[24] = 0;
   out_1615214032357491370[25] = 1;
   out_1615214032357491370[26] = 0;
   out_1615214032357491370[27] = 0;
   out_1615214032357491370[28] = 0;
   out_1615214032357491370[29] = 0;
   out_1615214032357491370[30] = 0;
   out_1615214032357491370[31] = 0;
   out_1615214032357491370[32] = 0;
   out_1615214032357491370[33] = 0;
   out_1615214032357491370[34] = 0;
   out_1615214032357491370[35] = 0;
   out_1615214032357491370[36] = 0;
   out_1615214032357491370[37] = 0;
   out_1615214032357491370[38] = 0;
   out_1615214032357491370[39] = 0;
   out_1615214032357491370[40] = 0;
   out_1615214032357491370[41] = 0;
   out_1615214032357491370[42] = 0;
   out_1615214032357491370[43] = 0;
   out_1615214032357491370[44] = 1;
   out_1615214032357491370[45] = 0;
   out_1615214032357491370[46] = 0;
   out_1615214032357491370[47] = 0;
   out_1615214032357491370[48] = 0;
   out_1615214032357491370[49] = 0;
   out_1615214032357491370[50] = 0;
   out_1615214032357491370[51] = 0;
   out_1615214032357491370[52] = 0;
   out_1615214032357491370[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_867342344380239798) {
  err_fun(nom_x, delta_x, out_867342344380239798);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2946458972277190645) {
  inv_err_fun(nom_x, true_x, out_2946458972277190645);
}
void pose_H_mod_fun(double *state, double *out_8034808007713849348) {
  H_mod_fun(state, out_8034808007713849348);
}
void pose_f_fun(double *state, double dt, double *out_5448742405462655453) {
  f_fun(state,  dt, out_5448742405462655453);
}
void pose_F_fun(double *state, double dt, double *out_582733379073092242) {
  F_fun(state,  dt, out_582733379073092242);
}
void pose_h_4(double *state, double *unused, double *out_959952002277923346) {
  h_4(state, unused, out_959952002277923346);
}
void pose_H_4(double *state, double *unused, double *out_1467574399937880926) {
  H_4(state, unused, out_1467574399937880926);
}
void pose_h_10(double *state, double *unused, double *out_315403293584823803) {
  h_10(state, unused, out_315403293584823803);
}
void pose_H_10(double *state, double *unused, double *out_2334763542090568144) {
  H_10(state, unused, out_2334763542090568144);
}
void pose_h_13(double *state, double *unused, double *out_5013407308002664142) {
  h_13(state, unused, out_5013407308002664142);
}
void pose_H_13(double *state, double *unused, double *out_4679848225270213727) {
  H_13(state, unused, out_4679848225270213727);
}
void pose_h_14(double *state, double *unused, double *out_6338305732819674146) {
  h_14(state, unused, out_6338305732819674146);
}
void pose_H_14(double *state, double *unused, double *out_1615214032357491370) {
  H_14(state, unused, out_1615214032357491370);
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
