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
void err_fun(double *nom_x, double *delta_x, double *out_8335705466919993114) {
   out_8335705466919993114[0] = delta_x[0] + nom_x[0];
   out_8335705466919993114[1] = delta_x[1] + nom_x[1];
   out_8335705466919993114[2] = delta_x[2] + nom_x[2];
   out_8335705466919993114[3] = delta_x[3] + nom_x[3];
   out_8335705466919993114[4] = delta_x[4] + nom_x[4];
   out_8335705466919993114[5] = delta_x[5] + nom_x[5];
   out_8335705466919993114[6] = delta_x[6] + nom_x[6];
   out_8335705466919993114[7] = delta_x[7] + nom_x[7];
   out_8335705466919993114[8] = delta_x[8] + nom_x[8];
   out_8335705466919993114[9] = delta_x[9] + nom_x[9];
   out_8335705466919993114[10] = delta_x[10] + nom_x[10];
   out_8335705466919993114[11] = delta_x[11] + nom_x[11];
   out_8335705466919993114[12] = delta_x[12] + nom_x[12];
   out_8335705466919993114[13] = delta_x[13] + nom_x[13];
   out_8335705466919993114[14] = delta_x[14] + nom_x[14];
   out_8335705466919993114[15] = delta_x[15] + nom_x[15];
   out_8335705466919993114[16] = delta_x[16] + nom_x[16];
   out_8335705466919993114[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_9209729373170481018) {
   out_9209729373170481018[0] = -nom_x[0] + true_x[0];
   out_9209729373170481018[1] = -nom_x[1] + true_x[1];
   out_9209729373170481018[2] = -nom_x[2] + true_x[2];
   out_9209729373170481018[3] = -nom_x[3] + true_x[3];
   out_9209729373170481018[4] = -nom_x[4] + true_x[4];
   out_9209729373170481018[5] = -nom_x[5] + true_x[5];
   out_9209729373170481018[6] = -nom_x[6] + true_x[6];
   out_9209729373170481018[7] = -nom_x[7] + true_x[7];
   out_9209729373170481018[8] = -nom_x[8] + true_x[8];
   out_9209729373170481018[9] = -nom_x[9] + true_x[9];
   out_9209729373170481018[10] = -nom_x[10] + true_x[10];
   out_9209729373170481018[11] = -nom_x[11] + true_x[11];
   out_9209729373170481018[12] = -nom_x[12] + true_x[12];
   out_9209729373170481018[13] = -nom_x[13] + true_x[13];
   out_9209729373170481018[14] = -nom_x[14] + true_x[14];
   out_9209729373170481018[15] = -nom_x[15] + true_x[15];
   out_9209729373170481018[16] = -nom_x[16] + true_x[16];
   out_9209729373170481018[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5876727134914556900) {
   out_5876727134914556900[0] = 1.0;
   out_5876727134914556900[1] = 0.0;
   out_5876727134914556900[2] = 0.0;
   out_5876727134914556900[3] = 0.0;
   out_5876727134914556900[4] = 0.0;
   out_5876727134914556900[5] = 0.0;
   out_5876727134914556900[6] = 0.0;
   out_5876727134914556900[7] = 0.0;
   out_5876727134914556900[8] = 0.0;
   out_5876727134914556900[9] = 0.0;
   out_5876727134914556900[10] = 0.0;
   out_5876727134914556900[11] = 0.0;
   out_5876727134914556900[12] = 0.0;
   out_5876727134914556900[13] = 0.0;
   out_5876727134914556900[14] = 0.0;
   out_5876727134914556900[15] = 0.0;
   out_5876727134914556900[16] = 0.0;
   out_5876727134914556900[17] = 0.0;
   out_5876727134914556900[18] = 0.0;
   out_5876727134914556900[19] = 1.0;
   out_5876727134914556900[20] = 0.0;
   out_5876727134914556900[21] = 0.0;
   out_5876727134914556900[22] = 0.0;
   out_5876727134914556900[23] = 0.0;
   out_5876727134914556900[24] = 0.0;
   out_5876727134914556900[25] = 0.0;
   out_5876727134914556900[26] = 0.0;
   out_5876727134914556900[27] = 0.0;
   out_5876727134914556900[28] = 0.0;
   out_5876727134914556900[29] = 0.0;
   out_5876727134914556900[30] = 0.0;
   out_5876727134914556900[31] = 0.0;
   out_5876727134914556900[32] = 0.0;
   out_5876727134914556900[33] = 0.0;
   out_5876727134914556900[34] = 0.0;
   out_5876727134914556900[35] = 0.0;
   out_5876727134914556900[36] = 0.0;
   out_5876727134914556900[37] = 0.0;
   out_5876727134914556900[38] = 1.0;
   out_5876727134914556900[39] = 0.0;
   out_5876727134914556900[40] = 0.0;
   out_5876727134914556900[41] = 0.0;
   out_5876727134914556900[42] = 0.0;
   out_5876727134914556900[43] = 0.0;
   out_5876727134914556900[44] = 0.0;
   out_5876727134914556900[45] = 0.0;
   out_5876727134914556900[46] = 0.0;
   out_5876727134914556900[47] = 0.0;
   out_5876727134914556900[48] = 0.0;
   out_5876727134914556900[49] = 0.0;
   out_5876727134914556900[50] = 0.0;
   out_5876727134914556900[51] = 0.0;
   out_5876727134914556900[52] = 0.0;
   out_5876727134914556900[53] = 0.0;
   out_5876727134914556900[54] = 0.0;
   out_5876727134914556900[55] = 0.0;
   out_5876727134914556900[56] = 0.0;
   out_5876727134914556900[57] = 1.0;
   out_5876727134914556900[58] = 0.0;
   out_5876727134914556900[59] = 0.0;
   out_5876727134914556900[60] = 0.0;
   out_5876727134914556900[61] = 0.0;
   out_5876727134914556900[62] = 0.0;
   out_5876727134914556900[63] = 0.0;
   out_5876727134914556900[64] = 0.0;
   out_5876727134914556900[65] = 0.0;
   out_5876727134914556900[66] = 0.0;
   out_5876727134914556900[67] = 0.0;
   out_5876727134914556900[68] = 0.0;
   out_5876727134914556900[69] = 0.0;
   out_5876727134914556900[70] = 0.0;
   out_5876727134914556900[71] = 0.0;
   out_5876727134914556900[72] = 0.0;
   out_5876727134914556900[73] = 0.0;
   out_5876727134914556900[74] = 0.0;
   out_5876727134914556900[75] = 0.0;
   out_5876727134914556900[76] = 1.0;
   out_5876727134914556900[77] = 0.0;
   out_5876727134914556900[78] = 0.0;
   out_5876727134914556900[79] = 0.0;
   out_5876727134914556900[80] = 0.0;
   out_5876727134914556900[81] = 0.0;
   out_5876727134914556900[82] = 0.0;
   out_5876727134914556900[83] = 0.0;
   out_5876727134914556900[84] = 0.0;
   out_5876727134914556900[85] = 0.0;
   out_5876727134914556900[86] = 0.0;
   out_5876727134914556900[87] = 0.0;
   out_5876727134914556900[88] = 0.0;
   out_5876727134914556900[89] = 0.0;
   out_5876727134914556900[90] = 0.0;
   out_5876727134914556900[91] = 0.0;
   out_5876727134914556900[92] = 0.0;
   out_5876727134914556900[93] = 0.0;
   out_5876727134914556900[94] = 0.0;
   out_5876727134914556900[95] = 1.0;
   out_5876727134914556900[96] = 0.0;
   out_5876727134914556900[97] = 0.0;
   out_5876727134914556900[98] = 0.0;
   out_5876727134914556900[99] = 0.0;
   out_5876727134914556900[100] = 0.0;
   out_5876727134914556900[101] = 0.0;
   out_5876727134914556900[102] = 0.0;
   out_5876727134914556900[103] = 0.0;
   out_5876727134914556900[104] = 0.0;
   out_5876727134914556900[105] = 0.0;
   out_5876727134914556900[106] = 0.0;
   out_5876727134914556900[107] = 0.0;
   out_5876727134914556900[108] = 0.0;
   out_5876727134914556900[109] = 0.0;
   out_5876727134914556900[110] = 0.0;
   out_5876727134914556900[111] = 0.0;
   out_5876727134914556900[112] = 0.0;
   out_5876727134914556900[113] = 0.0;
   out_5876727134914556900[114] = 1.0;
   out_5876727134914556900[115] = 0.0;
   out_5876727134914556900[116] = 0.0;
   out_5876727134914556900[117] = 0.0;
   out_5876727134914556900[118] = 0.0;
   out_5876727134914556900[119] = 0.0;
   out_5876727134914556900[120] = 0.0;
   out_5876727134914556900[121] = 0.0;
   out_5876727134914556900[122] = 0.0;
   out_5876727134914556900[123] = 0.0;
   out_5876727134914556900[124] = 0.0;
   out_5876727134914556900[125] = 0.0;
   out_5876727134914556900[126] = 0.0;
   out_5876727134914556900[127] = 0.0;
   out_5876727134914556900[128] = 0.0;
   out_5876727134914556900[129] = 0.0;
   out_5876727134914556900[130] = 0.0;
   out_5876727134914556900[131] = 0.0;
   out_5876727134914556900[132] = 0.0;
   out_5876727134914556900[133] = 1.0;
   out_5876727134914556900[134] = 0.0;
   out_5876727134914556900[135] = 0.0;
   out_5876727134914556900[136] = 0.0;
   out_5876727134914556900[137] = 0.0;
   out_5876727134914556900[138] = 0.0;
   out_5876727134914556900[139] = 0.0;
   out_5876727134914556900[140] = 0.0;
   out_5876727134914556900[141] = 0.0;
   out_5876727134914556900[142] = 0.0;
   out_5876727134914556900[143] = 0.0;
   out_5876727134914556900[144] = 0.0;
   out_5876727134914556900[145] = 0.0;
   out_5876727134914556900[146] = 0.0;
   out_5876727134914556900[147] = 0.0;
   out_5876727134914556900[148] = 0.0;
   out_5876727134914556900[149] = 0.0;
   out_5876727134914556900[150] = 0.0;
   out_5876727134914556900[151] = 0.0;
   out_5876727134914556900[152] = 1.0;
   out_5876727134914556900[153] = 0.0;
   out_5876727134914556900[154] = 0.0;
   out_5876727134914556900[155] = 0.0;
   out_5876727134914556900[156] = 0.0;
   out_5876727134914556900[157] = 0.0;
   out_5876727134914556900[158] = 0.0;
   out_5876727134914556900[159] = 0.0;
   out_5876727134914556900[160] = 0.0;
   out_5876727134914556900[161] = 0.0;
   out_5876727134914556900[162] = 0.0;
   out_5876727134914556900[163] = 0.0;
   out_5876727134914556900[164] = 0.0;
   out_5876727134914556900[165] = 0.0;
   out_5876727134914556900[166] = 0.0;
   out_5876727134914556900[167] = 0.0;
   out_5876727134914556900[168] = 0.0;
   out_5876727134914556900[169] = 0.0;
   out_5876727134914556900[170] = 0.0;
   out_5876727134914556900[171] = 1.0;
   out_5876727134914556900[172] = 0.0;
   out_5876727134914556900[173] = 0.0;
   out_5876727134914556900[174] = 0.0;
   out_5876727134914556900[175] = 0.0;
   out_5876727134914556900[176] = 0.0;
   out_5876727134914556900[177] = 0.0;
   out_5876727134914556900[178] = 0.0;
   out_5876727134914556900[179] = 0.0;
   out_5876727134914556900[180] = 0.0;
   out_5876727134914556900[181] = 0.0;
   out_5876727134914556900[182] = 0.0;
   out_5876727134914556900[183] = 0.0;
   out_5876727134914556900[184] = 0.0;
   out_5876727134914556900[185] = 0.0;
   out_5876727134914556900[186] = 0.0;
   out_5876727134914556900[187] = 0.0;
   out_5876727134914556900[188] = 0.0;
   out_5876727134914556900[189] = 0.0;
   out_5876727134914556900[190] = 1.0;
   out_5876727134914556900[191] = 0.0;
   out_5876727134914556900[192] = 0.0;
   out_5876727134914556900[193] = 0.0;
   out_5876727134914556900[194] = 0.0;
   out_5876727134914556900[195] = 0.0;
   out_5876727134914556900[196] = 0.0;
   out_5876727134914556900[197] = 0.0;
   out_5876727134914556900[198] = 0.0;
   out_5876727134914556900[199] = 0.0;
   out_5876727134914556900[200] = 0.0;
   out_5876727134914556900[201] = 0.0;
   out_5876727134914556900[202] = 0.0;
   out_5876727134914556900[203] = 0.0;
   out_5876727134914556900[204] = 0.0;
   out_5876727134914556900[205] = 0.0;
   out_5876727134914556900[206] = 0.0;
   out_5876727134914556900[207] = 0.0;
   out_5876727134914556900[208] = 0.0;
   out_5876727134914556900[209] = 1.0;
   out_5876727134914556900[210] = 0.0;
   out_5876727134914556900[211] = 0.0;
   out_5876727134914556900[212] = 0.0;
   out_5876727134914556900[213] = 0.0;
   out_5876727134914556900[214] = 0.0;
   out_5876727134914556900[215] = 0.0;
   out_5876727134914556900[216] = 0.0;
   out_5876727134914556900[217] = 0.0;
   out_5876727134914556900[218] = 0.0;
   out_5876727134914556900[219] = 0.0;
   out_5876727134914556900[220] = 0.0;
   out_5876727134914556900[221] = 0.0;
   out_5876727134914556900[222] = 0.0;
   out_5876727134914556900[223] = 0.0;
   out_5876727134914556900[224] = 0.0;
   out_5876727134914556900[225] = 0.0;
   out_5876727134914556900[226] = 0.0;
   out_5876727134914556900[227] = 0.0;
   out_5876727134914556900[228] = 1.0;
   out_5876727134914556900[229] = 0.0;
   out_5876727134914556900[230] = 0.0;
   out_5876727134914556900[231] = 0.0;
   out_5876727134914556900[232] = 0.0;
   out_5876727134914556900[233] = 0.0;
   out_5876727134914556900[234] = 0.0;
   out_5876727134914556900[235] = 0.0;
   out_5876727134914556900[236] = 0.0;
   out_5876727134914556900[237] = 0.0;
   out_5876727134914556900[238] = 0.0;
   out_5876727134914556900[239] = 0.0;
   out_5876727134914556900[240] = 0.0;
   out_5876727134914556900[241] = 0.0;
   out_5876727134914556900[242] = 0.0;
   out_5876727134914556900[243] = 0.0;
   out_5876727134914556900[244] = 0.0;
   out_5876727134914556900[245] = 0.0;
   out_5876727134914556900[246] = 0.0;
   out_5876727134914556900[247] = 1.0;
   out_5876727134914556900[248] = 0.0;
   out_5876727134914556900[249] = 0.0;
   out_5876727134914556900[250] = 0.0;
   out_5876727134914556900[251] = 0.0;
   out_5876727134914556900[252] = 0.0;
   out_5876727134914556900[253] = 0.0;
   out_5876727134914556900[254] = 0.0;
   out_5876727134914556900[255] = 0.0;
   out_5876727134914556900[256] = 0.0;
   out_5876727134914556900[257] = 0.0;
   out_5876727134914556900[258] = 0.0;
   out_5876727134914556900[259] = 0.0;
   out_5876727134914556900[260] = 0.0;
   out_5876727134914556900[261] = 0.0;
   out_5876727134914556900[262] = 0.0;
   out_5876727134914556900[263] = 0.0;
   out_5876727134914556900[264] = 0.0;
   out_5876727134914556900[265] = 0.0;
   out_5876727134914556900[266] = 1.0;
   out_5876727134914556900[267] = 0.0;
   out_5876727134914556900[268] = 0.0;
   out_5876727134914556900[269] = 0.0;
   out_5876727134914556900[270] = 0.0;
   out_5876727134914556900[271] = 0.0;
   out_5876727134914556900[272] = 0.0;
   out_5876727134914556900[273] = 0.0;
   out_5876727134914556900[274] = 0.0;
   out_5876727134914556900[275] = 0.0;
   out_5876727134914556900[276] = 0.0;
   out_5876727134914556900[277] = 0.0;
   out_5876727134914556900[278] = 0.0;
   out_5876727134914556900[279] = 0.0;
   out_5876727134914556900[280] = 0.0;
   out_5876727134914556900[281] = 0.0;
   out_5876727134914556900[282] = 0.0;
   out_5876727134914556900[283] = 0.0;
   out_5876727134914556900[284] = 0.0;
   out_5876727134914556900[285] = 1.0;
   out_5876727134914556900[286] = 0.0;
   out_5876727134914556900[287] = 0.0;
   out_5876727134914556900[288] = 0.0;
   out_5876727134914556900[289] = 0.0;
   out_5876727134914556900[290] = 0.0;
   out_5876727134914556900[291] = 0.0;
   out_5876727134914556900[292] = 0.0;
   out_5876727134914556900[293] = 0.0;
   out_5876727134914556900[294] = 0.0;
   out_5876727134914556900[295] = 0.0;
   out_5876727134914556900[296] = 0.0;
   out_5876727134914556900[297] = 0.0;
   out_5876727134914556900[298] = 0.0;
   out_5876727134914556900[299] = 0.0;
   out_5876727134914556900[300] = 0.0;
   out_5876727134914556900[301] = 0.0;
   out_5876727134914556900[302] = 0.0;
   out_5876727134914556900[303] = 0.0;
   out_5876727134914556900[304] = 1.0;
   out_5876727134914556900[305] = 0.0;
   out_5876727134914556900[306] = 0.0;
   out_5876727134914556900[307] = 0.0;
   out_5876727134914556900[308] = 0.0;
   out_5876727134914556900[309] = 0.0;
   out_5876727134914556900[310] = 0.0;
   out_5876727134914556900[311] = 0.0;
   out_5876727134914556900[312] = 0.0;
   out_5876727134914556900[313] = 0.0;
   out_5876727134914556900[314] = 0.0;
   out_5876727134914556900[315] = 0.0;
   out_5876727134914556900[316] = 0.0;
   out_5876727134914556900[317] = 0.0;
   out_5876727134914556900[318] = 0.0;
   out_5876727134914556900[319] = 0.0;
   out_5876727134914556900[320] = 0.0;
   out_5876727134914556900[321] = 0.0;
   out_5876727134914556900[322] = 0.0;
   out_5876727134914556900[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_1779979971211032045) {
   out_1779979971211032045[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_1779979971211032045[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_1779979971211032045[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_1779979971211032045[3] = dt*state[12] + state[3];
   out_1779979971211032045[4] = dt*state[13] + state[4];
   out_1779979971211032045[5] = dt*state[14] + state[5];
   out_1779979971211032045[6] = state[6];
   out_1779979971211032045[7] = state[7];
   out_1779979971211032045[8] = state[8];
   out_1779979971211032045[9] = state[9];
   out_1779979971211032045[10] = state[10];
   out_1779979971211032045[11] = state[11];
   out_1779979971211032045[12] = state[12];
   out_1779979971211032045[13] = state[13];
   out_1779979971211032045[14] = state[14];
   out_1779979971211032045[15] = state[15];
   out_1779979971211032045[16] = state[16];
   out_1779979971211032045[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8981529364252963210) {
   out_8981529364252963210[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8981529364252963210[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8981529364252963210[2] = 0;
   out_8981529364252963210[3] = 0;
   out_8981529364252963210[4] = 0;
   out_8981529364252963210[5] = 0;
   out_8981529364252963210[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8981529364252963210[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8981529364252963210[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8981529364252963210[9] = 0;
   out_8981529364252963210[10] = 0;
   out_8981529364252963210[11] = 0;
   out_8981529364252963210[12] = 0;
   out_8981529364252963210[13] = 0;
   out_8981529364252963210[14] = 0;
   out_8981529364252963210[15] = 0;
   out_8981529364252963210[16] = 0;
   out_8981529364252963210[17] = 0;
   out_8981529364252963210[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8981529364252963210[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8981529364252963210[20] = 0;
   out_8981529364252963210[21] = 0;
   out_8981529364252963210[22] = 0;
   out_8981529364252963210[23] = 0;
   out_8981529364252963210[24] = 0;
   out_8981529364252963210[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8981529364252963210[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8981529364252963210[27] = 0;
   out_8981529364252963210[28] = 0;
   out_8981529364252963210[29] = 0;
   out_8981529364252963210[30] = 0;
   out_8981529364252963210[31] = 0;
   out_8981529364252963210[32] = 0;
   out_8981529364252963210[33] = 0;
   out_8981529364252963210[34] = 0;
   out_8981529364252963210[35] = 0;
   out_8981529364252963210[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8981529364252963210[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8981529364252963210[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8981529364252963210[39] = 0;
   out_8981529364252963210[40] = 0;
   out_8981529364252963210[41] = 0;
   out_8981529364252963210[42] = 0;
   out_8981529364252963210[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8981529364252963210[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8981529364252963210[45] = 0;
   out_8981529364252963210[46] = 0;
   out_8981529364252963210[47] = 0;
   out_8981529364252963210[48] = 0;
   out_8981529364252963210[49] = 0;
   out_8981529364252963210[50] = 0;
   out_8981529364252963210[51] = 0;
   out_8981529364252963210[52] = 0;
   out_8981529364252963210[53] = 0;
   out_8981529364252963210[54] = 0;
   out_8981529364252963210[55] = 0;
   out_8981529364252963210[56] = 0;
   out_8981529364252963210[57] = 1;
   out_8981529364252963210[58] = 0;
   out_8981529364252963210[59] = 0;
   out_8981529364252963210[60] = 0;
   out_8981529364252963210[61] = 0;
   out_8981529364252963210[62] = 0;
   out_8981529364252963210[63] = 0;
   out_8981529364252963210[64] = 0;
   out_8981529364252963210[65] = 0;
   out_8981529364252963210[66] = dt;
   out_8981529364252963210[67] = 0;
   out_8981529364252963210[68] = 0;
   out_8981529364252963210[69] = 0;
   out_8981529364252963210[70] = 0;
   out_8981529364252963210[71] = 0;
   out_8981529364252963210[72] = 0;
   out_8981529364252963210[73] = 0;
   out_8981529364252963210[74] = 0;
   out_8981529364252963210[75] = 0;
   out_8981529364252963210[76] = 1;
   out_8981529364252963210[77] = 0;
   out_8981529364252963210[78] = 0;
   out_8981529364252963210[79] = 0;
   out_8981529364252963210[80] = 0;
   out_8981529364252963210[81] = 0;
   out_8981529364252963210[82] = 0;
   out_8981529364252963210[83] = 0;
   out_8981529364252963210[84] = 0;
   out_8981529364252963210[85] = dt;
   out_8981529364252963210[86] = 0;
   out_8981529364252963210[87] = 0;
   out_8981529364252963210[88] = 0;
   out_8981529364252963210[89] = 0;
   out_8981529364252963210[90] = 0;
   out_8981529364252963210[91] = 0;
   out_8981529364252963210[92] = 0;
   out_8981529364252963210[93] = 0;
   out_8981529364252963210[94] = 0;
   out_8981529364252963210[95] = 1;
   out_8981529364252963210[96] = 0;
   out_8981529364252963210[97] = 0;
   out_8981529364252963210[98] = 0;
   out_8981529364252963210[99] = 0;
   out_8981529364252963210[100] = 0;
   out_8981529364252963210[101] = 0;
   out_8981529364252963210[102] = 0;
   out_8981529364252963210[103] = 0;
   out_8981529364252963210[104] = dt;
   out_8981529364252963210[105] = 0;
   out_8981529364252963210[106] = 0;
   out_8981529364252963210[107] = 0;
   out_8981529364252963210[108] = 0;
   out_8981529364252963210[109] = 0;
   out_8981529364252963210[110] = 0;
   out_8981529364252963210[111] = 0;
   out_8981529364252963210[112] = 0;
   out_8981529364252963210[113] = 0;
   out_8981529364252963210[114] = 1;
   out_8981529364252963210[115] = 0;
   out_8981529364252963210[116] = 0;
   out_8981529364252963210[117] = 0;
   out_8981529364252963210[118] = 0;
   out_8981529364252963210[119] = 0;
   out_8981529364252963210[120] = 0;
   out_8981529364252963210[121] = 0;
   out_8981529364252963210[122] = 0;
   out_8981529364252963210[123] = 0;
   out_8981529364252963210[124] = 0;
   out_8981529364252963210[125] = 0;
   out_8981529364252963210[126] = 0;
   out_8981529364252963210[127] = 0;
   out_8981529364252963210[128] = 0;
   out_8981529364252963210[129] = 0;
   out_8981529364252963210[130] = 0;
   out_8981529364252963210[131] = 0;
   out_8981529364252963210[132] = 0;
   out_8981529364252963210[133] = 1;
   out_8981529364252963210[134] = 0;
   out_8981529364252963210[135] = 0;
   out_8981529364252963210[136] = 0;
   out_8981529364252963210[137] = 0;
   out_8981529364252963210[138] = 0;
   out_8981529364252963210[139] = 0;
   out_8981529364252963210[140] = 0;
   out_8981529364252963210[141] = 0;
   out_8981529364252963210[142] = 0;
   out_8981529364252963210[143] = 0;
   out_8981529364252963210[144] = 0;
   out_8981529364252963210[145] = 0;
   out_8981529364252963210[146] = 0;
   out_8981529364252963210[147] = 0;
   out_8981529364252963210[148] = 0;
   out_8981529364252963210[149] = 0;
   out_8981529364252963210[150] = 0;
   out_8981529364252963210[151] = 0;
   out_8981529364252963210[152] = 1;
   out_8981529364252963210[153] = 0;
   out_8981529364252963210[154] = 0;
   out_8981529364252963210[155] = 0;
   out_8981529364252963210[156] = 0;
   out_8981529364252963210[157] = 0;
   out_8981529364252963210[158] = 0;
   out_8981529364252963210[159] = 0;
   out_8981529364252963210[160] = 0;
   out_8981529364252963210[161] = 0;
   out_8981529364252963210[162] = 0;
   out_8981529364252963210[163] = 0;
   out_8981529364252963210[164] = 0;
   out_8981529364252963210[165] = 0;
   out_8981529364252963210[166] = 0;
   out_8981529364252963210[167] = 0;
   out_8981529364252963210[168] = 0;
   out_8981529364252963210[169] = 0;
   out_8981529364252963210[170] = 0;
   out_8981529364252963210[171] = 1;
   out_8981529364252963210[172] = 0;
   out_8981529364252963210[173] = 0;
   out_8981529364252963210[174] = 0;
   out_8981529364252963210[175] = 0;
   out_8981529364252963210[176] = 0;
   out_8981529364252963210[177] = 0;
   out_8981529364252963210[178] = 0;
   out_8981529364252963210[179] = 0;
   out_8981529364252963210[180] = 0;
   out_8981529364252963210[181] = 0;
   out_8981529364252963210[182] = 0;
   out_8981529364252963210[183] = 0;
   out_8981529364252963210[184] = 0;
   out_8981529364252963210[185] = 0;
   out_8981529364252963210[186] = 0;
   out_8981529364252963210[187] = 0;
   out_8981529364252963210[188] = 0;
   out_8981529364252963210[189] = 0;
   out_8981529364252963210[190] = 1;
   out_8981529364252963210[191] = 0;
   out_8981529364252963210[192] = 0;
   out_8981529364252963210[193] = 0;
   out_8981529364252963210[194] = 0;
   out_8981529364252963210[195] = 0;
   out_8981529364252963210[196] = 0;
   out_8981529364252963210[197] = 0;
   out_8981529364252963210[198] = 0;
   out_8981529364252963210[199] = 0;
   out_8981529364252963210[200] = 0;
   out_8981529364252963210[201] = 0;
   out_8981529364252963210[202] = 0;
   out_8981529364252963210[203] = 0;
   out_8981529364252963210[204] = 0;
   out_8981529364252963210[205] = 0;
   out_8981529364252963210[206] = 0;
   out_8981529364252963210[207] = 0;
   out_8981529364252963210[208] = 0;
   out_8981529364252963210[209] = 1;
   out_8981529364252963210[210] = 0;
   out_8981529364252963210[211] = 0;
   out_8981529364252963210[212] = 0;
   out_8981529364252963210[213] = 0;
   out_8981529364252963210[214] = 0;
   out_8981529364252963210[215] = 0;
   out_8981529364252963210[216] = 0;
   out_8981529364252963210[217] = 0;
   out_8981529364252963210[218] = 0;
   out_8981529364252963210[219] = 0;
   out_8981529364252963210[220] = 0;
   out_8981529364252963210[221] = 0;
   out_8981529364252963210[222] = 0;
   out_8981529364252963210[223] = 0;
   out_8981529364252963210[224] = 0;
   out_8981529364252963210[225] = 0;
   out_8981529364252963210[226] = 0;
   out_8981529364252963210[227] = 0;
   out_8981529364252963210[228] = 1;
   out_8981529364252963210[229] = 0;
   out_8981529364252963210[230] = 0;
   out_8981529364252963210[231] = 0;
   out_8981529364252963210[232] = 0;
   out_8981529364252963210[233] = 0;
   out_8981529364252963210[234] = 0;
   out_8981529364252963210[235] = 0;
   out_8981529364252963210[236] = 0;
   out_8981529364252963210[237] = 0;
   out_8981529364252963210[238] = 0;
   out_8981529364252963210[239] = 0;
   out_8981529364252963210[240] = 0;
   out_8981529364252963210[241] = 0;
   out_8981529364252963210[242] = 0;
   out_8981529364252963210[243] = 0;
   out_8981529364252963210[244] = 0;
   out_8981529364252963210[245] = 0;
   out_8981529364252963210[246] = 0;
   out_8981529364252963210[247] = 1;
   out_8981529364252963210[248] = 0;
   out_8981529364252963210[249] = 0;
   out_8981529364252963210[250] = 0;
   out_8981529364252963210[251] = 0;
   out_8981529364252963210[252] = 0;
   out_8981529364252963210[253] = 0;
   out_8981529364252963210[254] = 0;
   out_8981529364252963210[255] = 0;
   out_8981529364252963210[256] = 0;
   out_8981529364252963210[257] = 0;
   out_8981529364252963210[258] = 0;
   out_8981529364252963210[259] = 0;
   out_8981529364252963210[260] = 0;
   out_8981529364252963210[261] = 0;
   out_8981529364252963210[262] = 0;
   out_8981529364252963210[263] = 0;
   out_8981529364252963210[264] = 0;
   out_8981529364252963210[265] = 0;
   out_8981529364252963210[266] = 1;
   out_8981529364252963210[267] = 0;
   out_8981529364252963210[268] = 0;
   out_8981529364252963210[269] = 0;
   out_8981529364252963210[270] = 0;
   out_8981529364252963210[271] = 0;
   out_8981529364252963210[272] = 0;
   out_8981529364252963210[273] = 0;
   out_8981529364252963210[274] = 0;
   out_8981529364252963210[275] = 0;
   out_8981529364252963210[276] = 0;
   out_8981529364252963210[277] = 0;
   out_8981529364252963210[278] = 0;
   out_8981529364252963210[279] = 0;
   out_8981529364252963210[280] = 0;
   out_8981529364252963210[281] = 0;
   out_8981529364252963210[282] = 0;
   out_8981529364252963210[283] = 0;
   out_8981529364252963210[284] = 0;
   out_8981529364252963210[285] = 1;
   out_8981529364252963210[286] = 0;
   out_8981529364252963210[287] = 0;
   out_8981529364252963210[288] = 0;
   out_8981529364252963210[289] = 0;
   out_8981529364252963210[290] = 0;
   out_8981529364252963210[291] = 0;
   out_8981529364252963210[292] = 0;
   out_8981529364252963210[293] = 0;
   out_8981529364252963210[294] = 0;
   out_8981529364252963210[295] = 0;
   out_8981529364252963210[296] = 0;
   out_8981529364252963210[297] = 0;
   out_8981529364252963210[298] = 0;
   out_8981529364252963210[299] = 0;
   out_8981529364252963210[300] = 0;
   out_8981529364252963210[301] = 0;
   out_8981529364252963210[302] = 0;
   out_8981529364252963210[303] = 0;
   out_8981529364252963210[304] = 1;
   out_8981529364252963210[305] = 0;
   out_8981529364252963210[306] = 0;
   out_8981529364252963210[307] = 0;
   out_8981529364252963210[308] = 0;
   out_8981529364252963210[309] = 0;
   out_8981529364252963210[310] = 0;
   out_8981529364252963210[311] = 0;
   out_8981529364252963210[312] = 0;
   out_8981529364252963210[313] = 0;
   out_8981529364252963210[314] = 0;
   out_8981529364252963210[315] = 0;
   out_8981529364252963210[316] = 0;
   out_8981529364252963210[317] = 0;
   out_8981529364252963210[318] = 0;
   out_8981529364252963210[319] = 0;
   out_8981529364252963210[320] = 0;
   out_8981529364252963210[321] = 0;
   out_8981529364252963210[322] = 0;
   out_8981529364252963210[323] = 1;
}
void h_4(double *state, double *unused, double *out_6202861285607844763) {
   out_6202861285607844763[0] = state[6] + state[9];
   out_6202861285607844763[1] = state[7] + state[10];
   out_6202861285607844763[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3067634531143264442) {
   out_3067634531143264442[0] = 0;
   out_3067634531143264442[1] = 0;
   out_3067634531143264442[2] = 0;
   out_3067634531143264442[3] = 0;
   out_3067634531143264442[4] = 0;
   out_3067634531143264442[5] = 0;
   out_3067634531143264442[6] = 1;
   out_3067634531143264442[7] = 0;
   out_3067634531143264442[8] = 0;
   out_3067634531143264442[9] = 1;
   out_3067634531143264442[10] = 0;
   out_3067634531143264442[11] = 0;
   out_3067634531143264442[12] = 0;
   out_3067634531143264442[13] = 0;
   out_3067634531143264442[14] = 0;
   out_3067634531143264442[15] = 0;
   out_3067634531143264442[16] = 0;
   out_3067634531143264442[17] = 0;
   out_3067634531143264442[18] = 0;
   out_3067634531143264442[19] = 0;
   out_3067634531143264442[20] = 0;
   out_3067634531143264442[21] = 0;
   out_3067634531143264442[22] = 0;
   out_3067634531143264442[23] = 0;
   out_3067634531143264442[24] = 0;
   out_3067634531143264442[25] = 1;
   out_3067634531143264442[26] = 0;
   out_3067634531143264442[27] = 0;
   out_3067634531143264442[28] = 1;
   out_3067634531143264442[29] = 0;
   out_3067634531143264442[30] = 0;
   out_3067634531143264442[31] = 0;
   out_3067634531143264442[32] = 0;
   out_3067634531143264442[33] = 0;
   out_3067634531143264442[34] = 0;
   out_3067634531143264442[35] = 0;
   out_3067634531143264442[36] = 0;
   out_3067634531143264442[37] = 0;
   out_3067634531143264442[38] = 0;
   out_3067634531143264442[39] = 0;
   out_3067634531143264442[40] = 0;
   out_3067634531143264442[41] = 0;
   out_3067634531143264442[42] = 0;
   out_3067634531143264442[43] = 0;
   out_3067634531143264442[44] = 1;
   out_3067634531143264442[45] = 0;
   out_3067634531143264442[46] = 0;
   out_3067634531143264442[47] = 1;
   out_3067634531143264442[48] = 0;
   out_3067634531143264442[49] = 0;
   out_3067634531143264442[50] = 0;
   out_3067634531143264442[51] = 0;
   out_3067634531143264442[52] = 0;
   out_3067634531143264442[53] = 0;
}
void h_10(double *state, double *unused, double *out_193210824797184228) {
   out_193210824797184228[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_193210824797184228[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_193210824797184228[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8565894670277554621) {
   out_8565894670277554621[0] = 0;
   out_8565894670277554621[1] = 9.8100000000000005*cos(state[1]);
   out_8565894670277554621[2] = 0;
   out_8565894670277554621[3] = 0;
   out_8565894670277554621[4] = -state[8];
   out_8565894670277554621[5] = state[7];
   out_8565894670277554621[6] = 0;
   out_8565894670277554621[7] = state[5];
   out_8565894670277554621[8] = -state[4];
   out_8565894670277554621[9] = 0;
   out_8565894670277554621[10] = 0;
   out_8565894670277554621[11] = 0;
   out_8565894670277554621[12] = 1;
   out_8565894670277554621[13] = 0;
   out_8565894670277554621[14] = 0;
   out_8565894670277554621[15] = 1;
   out_8565894670277554621[16] = 0;
   out_8565894670277554621[17] = 0;
   out_8565894670277554621[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8565894670277554621[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8565894670277554621[20] = 0;
   out_8565894670277554621[21] = state[8];
   out_8565894670277554621[22] = 0;
   out_8565894670277554621[23] = -state[6];
   out_8565894670277554621[24] = -state[5];
   out_8565894670277554621[25] = 0;
   out_8565894670277554621[26] = state[3];
   out_8565894670277554621[27] = 0;
   out_8565894670277554621[28] = 0;
   out_8565894670277554621[29] = 0;
   out_8565894670277554621[30] = 0;
   out_8565894670277554621[31] = 1;
   out_8565894670277554621[32] = 0;
   out_8565894670277554621[33] = 0;
   out_8565894670277554621[34] = 1;
   out_8565894670277554621[35] = 0;
   out_8565894670277554621[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8565894670277554621[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8565894670277554621[38] = 0;
   out_8565894670277554621[39] = -state[7];
   out_8565894670277554621[40] = state[6];
   out_8565894670277554621[41] = 0;
   out_8565894670277554621[42] = state[4];
   out_8565894670277554621[43] = -state[3];
   out_8565894670277554621[44] = 0;
   out_8565894670277554621[45] = 0;
   out_8565894670277554621[46] = 0;
   out_8565894670277554621[47] = 0;
   out_8565894670277554621[48] = 0;
   out_8565894670277554621[49] = 0;
   out_8565894670277554621[50] = 1;
   out_8565894670277554621[51] = 0;
   out_8565894670277554621[52] = 0;
   out_8565894670277554621[53] = 1;
}
void h_13(double *state, double *unused, double *out_511558445403926696) {
   out_511558445403926696[0] = state[3];
   out_511558445403926696[1] = state[4];
   out_511558445403926696[2] = state[5];
}
void H_13(double *state, double *unused, double *out_144639294189068359) {
   out_144639294189068359[0] = 0;
   out_144639294189068359[1] = 0;
   out_144639294189068359[2] = 0;
   out_144639294189068359[3] = 1;
   out_144639294189068359[4] = 0;
   out_144639294189068359[5] = 0;
   out_144639294189068359[6] = 0;
   out_144639294189068359[7] = 0;
   out_144639294189068359[8] = 0;
   out_144639294189068359[9] = 0;
   out_144639294189068359[10] = 0;
   out_144639294189068359[11] = 0;
   out_144639294189068359[12] = 0;
   out_144639294189068359[13] = 0;
   out_144639294189068359[14] = 0;
   out_144639294189068359[15] = 0;
   out_144639294189068359[16] = 0;
   out_144639294189068359[17] = 0;
   out_144639294189068359[18] = 0;
   out_144639294189068359[19] = 0;
   out_144639294189068359[20] = 0;
   out_144639294189068359[21] = 0;
   out_144639294189068359[22] = 1;
   out_144639294189068359[23] = 0;
   out_144639294189068359[24] = 0;
   out_144639294189068359[25] = 0;
   out_144639294189068359[26] = 0;
   out_144639294189068359[27] = 0;
   out_144639294189068359[28] = 0;
   out_144639294189068359[29] = 0;
   out_144639294189068359[30] = 0;
   out_144639294189068359[31] = 0;
   out_144639294189068359[32] = 0;
   out_144639294189068359[33] = 0;
   out_144639294189068359[34] = 0;
   out_144639294189068359[35] = 0;
   out_144639294189068359[36] = 0;
   out_144639294189068359[37] = 0;
   out_144639294189068359[38] = 0;
   out_144639294189068359[39] = 0;
   out_144639294189068359[40] = 0;
   out_144639294189068359[41] = 1;
   out_144639294189068359[42] = 0;
   out_144639294189068359[43] = 0;
   out_144639294189068359[44] = 0;
   out_144639294189068359[45] = 0;
   out_144639294189068359[46] = 0;
   out_144639294189068359[47] = 0;
   out_144639294189068359[48] = 0;
   out_144639294189068359[49] = 0;
   out_144639294189068359[50] = 0;
   out_144639294189068359[51] = 0;
   out_144639294189068359[52] = 0;
   out_144639294189068359[53] = 0;
}
void h_14(double *state, double *unused, double *out_1260916310729678789) {
   out_1260916310729678789[0] = state[6];
   out_1260916310729678789[1] = state[7];
   out_1260916310729678789[2] = state[8];
}
void H_14(double *state, double *unused, double *out_895606325196220087) {
   out_895606325196220087[0] = 0;
   out_895606325196220087[1] = 0;
   out_895606325196220087[2] = 0;
   out_895606325196220087[3] = 0;
   out_895606325196220087[4] = 0;
   out_895606325196220087[5] = 0;
   out_895606325196220087[6] = 1;
   out_895606325196220087[7] = 0;
   out_895606325196220087[8] = 0;
   out_895606325196220087[9] = 0;
   out_895606325196220087[10] = 0;
   out_895606325196220087[11] = 0;
   out_895606325196220087[12] = 0;
   out_895606325196220087[13] = 0;
   out_895606325196220087[14] = 0;
   out_895606325196220087[15] = 0;
   out_895606325196220087[16] = 0;
   out_895606325196220087[17] = 0;
   out_895606325196220087[18] = 0;
   out_895606325196220087[19] = 0;
   out_895606325196220087[20] = 0;
   out_895606325196220087[21] = 0;
   out_895606325196220087[22] = 0;
   out_895606325196220087[23] = 0;
   out_895606325196220087[24] = 0;
   out_895606325196220087[25] = 1;
   out_895606325196220087[26] = 0;
   out_895606325196220087[27] = 0;
   out_895606325196220087[28] = 0;
   out_895606325196220087[29] = 0;
   out_895606325196220087[30] = 0;
   out_895606325196220087[31] = 0;
   out_895606325196220087[32] = 0;
   out_895606325196220087[33] = 0;
   out_895606325196220087[34] = 0;
   out_895606325196220087[35] = 0;
   out_895606325196220087[36] = 0;
   out_895606325196220087[37] = 0;
   out_895606325196220087[38] = 0;
   out_895606325196220087[39] = 0;
   out_895606325196220087[40] = 0;
   out_895606325196220087[41] = 0;
   out_895606325196220087[42] = 0;
   out_895606325196220087[43] = 0;
   out_895606325196220087[44] = 1;
   out_895606325196220087[45] = 0;
   out_895606325196220087[46] = 0;
   out_895606325196220087[47] = 0;
   out_895606325196220087[48] = 0;
   out_895606325196220087[49] = 0;
   out_895606325196220087[50] = 0;
   out_895606325196220087[51] = 0;
   out_895606325196220087[52] = 0;
   out_895606325196220087[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8335705466919993114) {
  err_fun(nom_x, delta_x, out_8335705466919993114);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_9209729373170481018) {
  inv_err_fun(nom_x, true_x, out_9209729373170481018);
}
void pose_H_mod_fun(double *state, double *out_5876727134914556900) {
  H_mod_fun(state, out_5876727134914556900);
}
void pose_f_fun(double *state, double dt, double *out_1779979971211032045) {
  f_fun(state,  dt, out_1779979971211032045);
}
void pose_F_fun(double *state, double dt, double *out_8981529364252963210) {
  F_fun(state,  dt, out_8981529364252963210);
}
void pose_h_4(double *state, double *unused, double *out_6202861285607844763) {
  h_4(state, unused, out_6202861285607844763);
}
void pose_H_4(double *state, double *unused, double *out_3067634531143264442) {
  H_4(state, unused, out_3067634531143264442);
}
void pose_h_10(double *state, double *unused, double *out_193210824797184228) {
  h_10(state, unused, out_193210824797184228);
}
void pose_H_10(double *state, double *unused, double *out_8565894670277554621) {
  H_10(state, unused, out_8565894670277554621);
}
void pose_h_13(double *state, double *unused, double *out_511558445403926696) {
  h_13(state, unused, out_511558445403926696);
}
void pose_H_13(double *state, double *unused, double *out_144639294189068359) {
  H_13(state, unused, out_144639294189068359);
}
void pose_h_14(double *state, double *unused, double *out_1260916310729678789) {
  h_14(state, unused, out_1260916310729678789);
}
void pose_H_14(double *state, double *unused, double *out_895606325196220087) {
  H_14(state, unused, out_895606325196220087);
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
