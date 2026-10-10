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
void err_fun(double *nom_x, double *delta_x, double *out_8743288361506485614) {
   out_8743288361506485614[0] = delta_x[0] + nom_x[0];
   out_8743288361506485614[1] = delta_x[1] + nom_x[1];
   out_8743288361506485614[2] = delta_x[2] + nom_x[2];
   out_8743288361506485614[3] = delta_x[3] + nom_x[3];
   out_8743288361506485614[4] = delta_x[4] + nom_x[4];
   out_8743288361506485614[5] = delta_x[5] + nom_x[5];
   out_8743288361506485614[6] = delta_x[6] + nom_x[6];
   out_8743288361506485614[7] = delta_x[7] + nom_x[7];
   out_8743288361506485614[8] = delta_x[8] + nom_x[8];
   out_8743288361506485614[9] = delta_x[9] + nom_x[9];
   out_8743288361506485614[10] = delta_x[10] + nom_x[10];
   out_8743288361506485614[11] = delta_x[11] + nom_x[11];
   out_8743288361506485614[12] = delta_x[12] + nom_x[12];
   out_8743288361506485614[13] = delta_x[13] + nom_x[13];
   out_8743288361506485614[14] = delta_x[14] + nom_x[14];
   out_8743288361506485614[15] = delta_x[15] + nom_x[15];
   out_8743288361506485614[16] = delta_x[16] + nom_x[16];
   out_8743288361506485614[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7700232313042684193) {
   out_7700232313042684193[0] = -nom_x[0] + true_x[0];
   out_7700232313042684193[1] = -nom_x[1] + true_x[1];
   out_7700232313042684193[2] = -nom_x[2] + true_x[2];
   out_7700232313042684193[3] = -nom_x[3] + true_x[3];
   out_7700232313042684193[4] = -nom_x[4] + true_x[4];
   out_7700232313042684193[5] = -nom_x[5] + true_x[5];
   out_7700232313042684193[6] = -nom_x[6] + true_x[6];
   out_7700232313042684193[7] = -nom_x[7] + true_x[7];
   out_7700232313042684193[8] = -nom_x[8] + true_x[8];
   out_7700232313042684193[9] = -nom_x[9] + true_x[9];
   out_7700232313042684193[10] = -nom_x[10] + true_x[10];
   out_7700232313042684193[11] = -nom_x[11] + true_x[11];
   out_7700232313042684193[12] = -nom_x[12] + true_x[12];
   out_7700232313042684193[13] = -nom_x[13] + true_x[13];
   out_7700232313042684193[14] = -nom_x[14] + true_x[14];
   out_7700232313042684193[15] = -nom_x[15] + true_x[15];
   out_7700232313042684193[16] = -nom_x[16] + true_x[16];
   out_7700232313042684193[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5879762199447615362) {
   out_5879762199447615362[0] = 1.0;
   out_5879762199447615362[1] = 0.0;
   out_5879762199447615362[2] = 0.0;
   out_5879762199447615362[3] = 0.0;
   out_5879762199447615362[4] = 0.0;
   out_5879762199447615362[5] = 0.0;
   out_5879762199447615362[6] = 0.0;
   out_5879762199447615362[7] = 0.0;
   out_5879762199447615362[8] = 0.0;
   out_5879762199447615362[9] = 0.0;
   out_5879762199447615362[10] = 0.0;
   out_5879762199447615362[11] = 0.0;
   out_5879762199447615362[12] = 0.0;
   out_5879762199447615362[13] = 0.0;
   out_5879762199447615362[14] = 0.0;
   out_5879762199447615362[15] = 0.0;
   out_5879762199447615362[16] = 0.0;
   out_5879762199447615362[17] = 0.0;
   out_5879762199447615362[18] = 0.0;
   out_5879762199447615362[19] = 1.0;
   out_5879762199447615362[20] = 0.0;
   out_5879762199447615362[21] = 0.0;
   out_5879762199447615362[22] = 0.0;
   out_5879762199447615362[23] = 0.0;
   out_5879762199447615362[24] = 0.0;
   out_5879762199447615362[25] = 0.0;
   out_5879762199447615362[26] = 0.0;
   out_5879762199447615362[27] = 0.0;
   out_5879762199447615362[28] = 0.0;
   out_5879762199447615362[29] = 0.0;
   out_5879762199447615362[30] = 0.0;
   out_5879762199447615362[31] = 0.0;
   out_5879762199447615362[32] = 0.0;
   out_5879762199447615362[33] = 0.0;
   out_5879762199447615362[34] = 0.0;
   out_5879762199447615362[35] = 0.0;
   out_5879762199447615362[36] = 0.0;
   out_5879762199447615362[37] = 0.0;
   out_5879762199447615362[38] = 1.0;
   out_5879762199447615362[39] = 0.0;
   out_5879762199447615362[40] = 0.0;
   out_5879762199447615362[41] = 0.0;
   out_5879762199447615362[42] = 0.0;
   out_5879762199447615362[43] = 0.0;
   out_5879762199447615362[44] = 0.0;
   out_5879762199447615362[45] = 0.0;
   out_5879762199447615362[46] = 0.0;
   out_5879762199447615362[47] = 0.0;
   out_5879762199447615362[48] = 0.0;
   out_5879762199447615362[49] = 0.0;
   out_5879762199447615362[50] = 0.0;
   out_5879762199447615362[51] = 0.0;
   out_5879762199447615362[52] = 0.0;
   out_5879762199447615362[53] = 0.0;
   out_5879762199447615362[54] = 0.0;
   out_5879762199447615362[55] = 0.0;
   out_5879762199447615362[56] = 0.0;
   out_5879762199447615362[57] = 1.0;
   out_5879762199447615362[58] = 0.0;
   out_5879762199447615362[59] = 0.0;
   out_5879762199447615362[60] = 0.0;
   out_5879762199447615362[61] = 0.0;
   out_5879762199447615362[62] = 0.0;
   out_5879762199447615362[63] = 0.0;
   out_5879762199447615362[64] = 0.0;
   out_5879762199447615362[65] = 0.0;
   out_5879762199447615362[66] = 0.0;
   out_5879762199447615362[67] = 0.0;
   out_5879762199447615362[68] = 0.0;
   out_5879762199447615362[69] = 0.0;
   out_5879762199447615362[70] = 0.0;
   out_5879762199447615362[71] = 0.0;
   out_5879762199447615362[72] = 0.0;
   out_5879762199447615362[73] = 0.0;
   out_5879762199447615362[74] = 0.0;
   out_5879762199447615362[75] = 0.0;
   out_5879762199447615362[76] = 1.0;
   out_5879762199447615362[77] = 0.0;
   out_5879762199447615362[78] = 0.0;
   out_5879762199447615362[79] = 0.0;
   out_5879762199447615362[80] = 0.0;
   out_5879762199447615362[81] = 0.0;
   out_5879762199447615362[82] = 0.0;
   out_5879762199447615362[83] = 0.0;
   out_5879762199447615362[84] = 0.0;
   out_5879762199447615362[85] = 0.0;
   out_5879762199447615362[86] = 0.0;
   out_5879762199447615362[87] = 0.0;
   out_5879762199447615362[88] = 0.0;
   out_5879762199447615362[89] = 0.0;
   out_5879762199447615362[90] = 0.0;
   out_5879762199447615362[91] = 0.0;
   out_5879762199447615362[92] = 0.0;
   out_5879762199447615362[93] = 0.0;
   out_5879762199447615362[94] = 0.0;
   out_5879762199447615362[95] = 1.0;
   out_5879762199447615362[96] = 0.0;
   out_5879762199447615362[97] = 0.0;
   out_5879762199447615362[98] = 0.0;
   out_5879762199447615362[99] = 0.0;
   out_5879762199447615362[100] = 0.0;
   out_5879762199447615362[101] = 0.0;
   out_5879762199447615362[102] = 0.0;
   out_5879762199447615362[103] = 0.0;
   out_5879762199447615362[104] = 0.0;
   out_5879762199447615362[105] = 0.0;
   out_5879762199447615362[106] = 0.0;
   out_5879762199447615362[107] = 0.0;
   out_5879762199447615362[108] = 0.0;
   out_5879762199447615362[109] = 0.0;
   out_5879762199447615362[110] = 0.0;
   out_5879762199447615362[111] = 0.0;
   out_5879762199447615362[112] = 0.0;
   out_5879762199447615362[113] = 0.0;
   out_5879762199447615362[114] = 1.0;
   out_5879762199447615362[115] = 0.0;
   out_5879762199447615362[116] = 0.0;
   out_5879762199447615362[117] = 0.0;
   out_5879762199447615362[118] = 0.0;
   out_5879762199447615362[119] = 0.0;
   out_5879762199447615362[120] = 0.0;
   out_5879762199447615362[121] = 0.0;
   out_5879762199447615362[122] = 0.0;
   out_5879762199447615362[123] = 0.0;
   out_5879762199447615362[124] = 0.0;
   out_5879762199447615362[125] = 0.0;
   out_5879762199447615362[126] = 0.0;
   out_5879762199447615362[127] = 0.0;
   out_5879762199447615362[128] = 0.0;
   out_5879762199447615362[129] = 0.0;
   out_5879762199447615362[130] = 0.0;
   out_5879762199447615362[131] = 0.0;
   out_5879762199447615362[132] = 0.0;
   out_5879762199447615362[133] = 1.0;
   out_5879762199447615362[134] = 0.0;
   out_5879762199447615362[135] = 0.0;
   out_5879762199447615362[136] = 0.0;
   out_5879762199447615362[137] = 0.0;
   out_5879762199447615362[138] = 0.0;
   out_5879762199447615362[139] = 0.0;
   out_5879762199447615362[140] = 0.0;
   out_5879762199447615362[141] = 0.0;
   out_5879762199447615362[142] = 0.0;
   out_5879762199447615362[143] = 0.0;
   out_5879762199447615362[144] = 0.0;
   out_5879762199447615362[145] = 0.0;
   out_5879762199447615362[146] = 0.0;
   out_5879762199447615362[147] = 0.0;
   out_5879762199447615362[148] = 0.0;
   out_5879762199447615362[149] = 0.0;
   out_5879762199447615362[150] = 0.0;
   out_5879762199447615362[151] = 0.0;
   out_5879762199447615362[152] = 1.0;
   out_5879762199447615362[153] = 0.0;
   out_5879762199447615362[154] = 0.0;
   out_5879762199447615362[155] = 0.0;
   out_5879762199447615362[156] = 0.0;
   out_5879762199447615362[157] = 0.0;
   out_5879762199447615362[158] = 0.0;
   out_5879762199447615362[159] = 0.0;
   out_5879762199447615362[160] = 0.0;
   out_5879762199447615362[161] = 0.0;
   out_5879762199447615362[162] = 0.0;
   out_5879762199447615362[163] = 0.0;
   out_5879762199447615362[164] = 0.0;
   out_5879762199447615362[165] = 0.0;
   out_5879762199447615362[166] = 0.0;
   out_5879762199447615362[167] = 0.0;
   out_5879762199447615362[168] = 0.0;
   out_5879762199447615362[169] = 0.0;
   out_5879762199447615362[170] = 0.0;
   out_5879762199447615362[171] = 1.0;
   out_5879762199447615362[172] = 0.0;
   out_5879762199447615362[173] = 0.0;
   out_5879762199447615362[174] = 0.0;
   out_5879762199447615362[175] = 0.0;
   out_5879762199447615362[176] = 0.0;
   out_5879762199447615362[177] = 0.0;
   out_5879762199447615362[178] = 0.0;
   out_5879762199447615362[179] = 0.0;
   out_5879762199447615362[180] = 0.0;
   out_5879762199447615362[181] = 0.0;
   out_5879762199447615362[182] = 0.0;
   out_5879762199447615362[183] = 0.0;
   out_5879762199447615362[184] = 0.0;
   out_5879762199447615362[185] = 0.0;
   out_5879762199447615362[186] = 0.0;
   out_5879762199447615362[187] = 0.0;
   out_5879762199447615362[188] = 0.0;
   out_5879762199447615362[189] = 0.0;
   out_5879762199447615362[190] = 1.0;
   out_5879762199447615362[191] = 0.0;
   out_5879762199447615362[192] = 0.0;
   out_5879762199447615362[193] = 0.0;
   out_5879762199447615362[194] = 0.0;
   out_5879762199447615362[195] = 0.0;
   out_5879762199447615362[196] = 0.0;
   out_5879762199447615362[197] = 0.0;
   out_5879762199447615362[198] = 0.0;
   out_5879762199447615362[199] = 0.0;
   out_5879762199447615362[200] = 0.0;
   out_5879762199447615362[201] = 0.0;
   out_5879762199447615362[202] = 0.0;
   out_5879762199447615362[203] = 0.0;
   out_5879762199447615362[204] = 0.0;
   out_5879762199447615362[205] = 0.0;
   out_5879762199447615362[206] = 0.0;
   out_5879762199447615362[207] = 0.0;
   out_5879762199447615362[208] = 0.0;
   out_5879762199447615362[209] = 1.0;
   out_5879762199447615362[210] = 0.0;
   out_5879762199447615362[211] = 0.0;
   out_5879762199447615362[212] = 0.0;
   out_5879762199447615362[213] = 0.0;
   out_5879762199447615362[214] = 0.0;
   out_5879762199447615362[215] = 0.0;
   out_5879762199447615362[216] = 0.0;
   out_5879762199447615362[217] = 0.0;
   out_5879762199447615362[218] = 0.0;
   out_5879762199447615362[219] = 0.0;
   out_5879762199447615362[220] = 0.0;
   out_5879762199447615362[221] = 0.0;
   out_5879762199447615362[222] = 0.0;
   out_5879762199447615362[223] = 0.0;
   out_5879762199447615362[224] = 0.0;
   out_5879762199447615362[225] = 0.0;
   out_5879762199447615362[226] = 0.0;
   out_5879762199447615362[227] = 0.0;
   out_5879762199447615362[228] = 1.0;
   out_5879762199447615362[229] = 0.0;
   out_5879762199447615362[230] = 0.0;
   out_5879762199447615362[231] = 0.0;
   out_5879762199447615362[232] = 0.0;
   out_5879762199447615362[233] = 0.0;
   out_5879762199447615362[234] = 0.0;
   out_5879762199447615362[235] = 0.0;
   out_5879762199447615362[236] = 0.0;
   out_5879762199447615362[237] = 0.0;
   out_5879762199447615362[238] = 0.0;
   out_5879762199447615362[239] = 0.0;
   out_5879762199447615362[240] = 0.0;
   out_5879762199447615362[241] = 0.0;
   out_5879762199447615362[242] = 0.0;
   out_5879762199447615362[243] = 0.0;
   out_5879762199447615362[244] = 0.0;
   out_5879762199447615362[245] = 0.0;
   out_5879762199447615362[246] = 0.0;
   out_5879762199447615362[247] = 1.0;
   out_5879762199447615362[248] = 0.0;
   out_5879762199447615362[249] = 0.0;
   out_5879762199447615362[250] = 0.0;
   out_5879762199447615362[251] = 0.0;
   out_5879762199447615362[252] = 0.0;
   out_5879762199447615362[253] = 0.0;
   out_5879762199447615362[254] = 0.0;
   out_5879762199447615362[255] = 0.0;
   out_5879762199447615362[256] = 0.0;
   out_5879762199447615362[257] = 0.0;
   out_5879762199447615362[258] = 0.0;
   out_5879762199447615362[259] = 0.0;
   out_5879762199447615362[260] = 0.0;
   out_5879762199447615362[261] = 0.0;
   out_5879762199447615362[262] = 0.0;
   out_5879762199447615362[263] = 0.0;
   out_5879762199447615362[264] = 0.0;
   out_5879762199447615362[265] = 0.0;
   out_5879762199447615362[266] = 1.0;
   out_5879762199447615362[267] = 0.0;
   out_5879762199447615362[268] = 0.0;
   out_5879762199447615362[269] = 0.0;
   out_5879762199447615362[270] = 0.0;
   out_5879762199447615362[271] = 0.0;
   out_5879762199447615362[272] = 0.0;
   out_5879762199447615362[273] = 0.0;
   out_5879762199447615362[274] = 0.0;
   out_5879762199447615362[275] = 0.0;
   out_5879762199447615362[276] = 0.0;
   out_5879762199447615362[277] = 0.0;
   out_5879762199447615362[278] = 0.0;
   out_5879762199447615362[279] = 0.0;
   out_5879762199447615362[280] = 0.0;
   out_5879762199447615362[281] = 0.0;
   out_5879762199447615362[282] = 0.0;
   out_5879762199447615362[283] = 0.0;
   out_5879762199447615362[284] = 0.0;
   out_5879762199447615362[285] = 1.0;
   out_5879762199447615362[286] = 0.0;
   out_5879762199447615362[287] = 0.0;
   out_5879762199447615362[288] = 0.0;
   out_5879762199447615362[289] = 0.0;
   out_5879762199447615362[290] = 0.0;
   out_5879762199447615362[291] = 0.0;
   out_5879762199447615362[292] = 0.0;
   out_5879762199447615362[293] = 0.0;
   out_5879762199447615362[294] = 0.0;
   out_5879762199447615362[295] = 0.0;
   out_5879762199447615362[296] = 0.0;
   out_5879762199447615362[297] = 0.0;
   out_5879762199447615362[298] = 0.0;
   out_5879762199447615362[299] = 0.0;
   out_5879762199447615362[300] = 0.0;
   out_5879762199447615362[301] = 0.0;
   out_5879762199447615362[302] = 0.0;
   out_5879762199447615362[303] = 0.0;
   out_5879762199447615362[304] = 1.0;
   out_5879762199447615362[305] = 0.0;
   out_5879762199447615362[306] = 0.0;
   out_5879762199447615362[307] = 0.0;
   out_5879762199447615362[308] = 0.0;
   out_5879762199447615362[309] = 0.0;
   out_5879762199447615362[310] = 0.0;
   out_5879762199447615362[311] = 0.0;
   out_5879762199447615362[312] = 0.0;
   out_5879762199447615362[313] = 0.0;
   out_5879762199447615362[314] = 0.0;
   out_5879762199447615362[315] = 0.0;
   out_5879762199447615362[316] = 0.0;
   out_5879762199447615362[317] = 0.0;
   out_5879762199447615362[318] = 0.0;
   out_5879762199447615362[319] = 0.0;
   out_5879762199447615362[320] = 0.0;
   out_5879762199447615362[321] = 0.0;
   out_5879762199447615362[322] = 0.0;
   out_5879762199447615362[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_9125558702662429027) {
   out_9125558702662429027[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_9125558702662429027[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_9125558702662429027[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_9125558702662429027[3] = dt*state[12] + state[3];
   out_9125558702662429027[4] = dt*state[13] + state[4];
   out_9125558702662429027[5] = dt*state[14] + state[5];
   out_9125558702662429027[6] = state[6];
   out_9125558702662429027[7] = state[7];
   out_9125558702662429027[8] = state[8];
   out_9125558702662429027[9] = state[9];
   out_9125558702662429027[10] = state[10];
   out_9125558702662429027[11] = state[11];
   out_9125558702662429027[12] = state[12];
   out_9125558702662429027[13] = state[13];
   out_9125558702662429027[14] = state[14];
   out_9125558702662429027[15] = state[15];
   out_9125558702662429027[16] = state[16];
   out_9125558702662429027[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7572446057115886568) {
   out_7572446057115886568[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7572446057115886568[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7572446057115886568[2] = 0;
   out_7572446057115886568[3] = 0;
   out_7572446057115886568[4] = 0;
   out_7572446057115886568[5] = 0;
   out_7572446057115886568[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7572446057115886568[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7572446057115886568[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7572446057115886568[9] = 0;
   out_7572446057115886568[10] = 0;
   out_7572446057115886568[11] = 0;
   out_7572446057115886568[12] = 0;
   out_7572446057115886568[13] = 0;
   out_7572446057115886568[14] = 0;
   out_7572446057115886568[15] = 0;
   out_7572446057115886568[16] = 0;
   out_7572446057115886568[17] = 0;
   out_7572446057115886568[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7572446057115886568[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7572446057115886568[20] = 0;
   out_7572446057115886568[21] = 0;
   out_7572446057115886568[22] = 0;
   out_7572446057115886568[23] = 0;
   out_7572446057115886568[24] = 0;
   out_7572446057115886568[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7572446057115886568[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7572446057115886568[27] = 0;
   out_7572446057115886568[28] = 0;
   out_7572446057115886568[29] = 0;
   out_7572446057115886568[30] = 0;
   out_7572446057115886568[31] = 0;
   out_7572446057115886568[32] = 0;
   out_7572446057115886568[33] = 0;
   out_7572446057115886568[34] = 0;
   out_7572446057115886568[35] = 0;
   out_7572446057115886568[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7572446057115886568[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7572446057115886568[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7572446057115886568[39] = 0;
   out_7572446057115886568[40] = 0;
   out_7572446057115886568[41] = 0;
   out_7572446057115886568[42] = 0;
   out_7572446057115886568[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7572446057115886568[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7572446057115886568[45] = 0;
   out_7572446057115886568[46] = 0;
   out_7572446057115886568[47] = 0;
   out_7572446057115886568[48] = 0;
   out_7572446057115886568[49] = 0;
   out_7572446057115886568[50] = 0;
   out_7572446057115886568[51] = 0;
   out_7572446057115886568[52] = 0;
   out_7572446057115886568[53] = 0;
   out_7572446057115886568[54] = 0;
   out_7572446057115886568[55] = 0;
   out_7572446057115886568[56] = 0;
   out_7572446057115886568[57] = 1;
   out_7572446057115886568[58] = 0;
   out_7572446057115886568[59] = 0;
   out_7572446057115886568[60] = 0;
   out_7572446057115886568[61] = 0;
   out_7572446057115886568[62] = 0;
   out_7572446057115886568[63] = 0;
   out_7572446057115886568[64] = 0;
   out_7572446057115886568[65] = 0;
   out_7572446057115886568[66] = dt;
   out_7572446057115886568[67] = 0;
   out_7572446057115886568[68] = 0;
   out_7572446057115886568[69] = 0;
   out_7572446057115886568[70] = 0;
   out_7572446057115886568[71] = 0;
   out_7572446057115886568[72] = 0;
   out_7572446057115886568[73] = 0;
   out_7572446057115886568[74] = 0;
   out_7572446057115886568[75] = 0;
   out_7572446057115886568[76] = 1;
   out_7572446057115886568[77] = 0;
   out_7572446057115886568[78] = 0;
   out_7572446057115886568[79] = 0;
   out_7572446057115886568[80] = 0;
   out_7572446057115886568[81] = 0;
   out_7572446057115886568[82] = 0;
   out_7572446057115886568[83] = 0;
   out_7572446057115886568[84] = 0;
   out_7572446057115886568[85] = dt;
   out_7572446057115886568[86] = 0;
   out_7572446057115886568[87] = 0;
   out_7572446057115886568[88] = 0;
   out_7572446057115886568[89] = 0;
   out_7572446057115886568[90] = 0;
   out_7572446057115886568[91] = 0;
   out_7572446057115886568[92] = 0;
   out_7572446057115886568[93] = 0;
   out_7572446057115886568[94] = 0;
   out_7572446057115886568[95] = 1;
   out_7572446057115886568[96] = 0;
   out_7572446057115886568[97] = 0;
   out_7572446057115886568[98] = 0;
   out_7572446057115886568[99] = 0;
   out_7572446057115886568[100] = 0;
   out_7572446057115886568[101] = 0;
   out_7572446057115886568[102] = 0;
   out_7572446057115886568[103] = 0;
   out_7572446057115886568[104] = dt;
   out_7572446057115886568[105] = 0;
   out_7572446057115886568[106] = 0;
   out_7572446057115886568[107] = 0;
   out_7572446057115886568[108] = 0;
   out_7572446057115886568[109] = 0;
   out_7572446057115886568[110] = 0;
   out_7572446057115886568[111] = 0;
   out_7572446057115886568[112] = 0;
   out_7572446057115886568[113] = 0;
   out_7572446057115886568[114] = 1;
   out_7572446057115886568[115] = 0;
   out_7572446057115886568[116] = 0;
   out_7572446057115886568[117] = 0;
   out_7572446057115886568[118] = 0;
   out_7572446057115886568[119] = 0;
   out_7572446057115886568[120] = 0;
   out_7572446057115886568[121] = 0;
   out_7572446057115886568[122] = 0;
   out_7572446057115886568[123] = 0;
   out_7572446057115886568[124] = 0;
   out_7572446057115886568[125] = 0;
   out_7572446057115886568[126] = 0;
   out_7572446057115886568[127] = 0;
   out_7572446057115886568[128] = 0;
   out_7572446057115886568[129] = 0;
   out_7572446057115886568[130] = 0;
   out_7572446057115886568[131] = 0;
   out_7572446057115886568[132] = 0;
   out_7572446057115886568[133] = 1;
   out_7572446057115886568[134] = 0;
   out_7572446057115886568[135] = 0;
   out_7572446057115886568[136] = 0;
   out_7572446057115886568[137] = 0;
   out_7572446057115886568[138] = 0;
   out_7572446057115886568[139] = 0;
   out_7572446057115886568[140] = 0;
   out_7572446057115886568[141] = 0;
   out_7572446057115886568[142] = 0;
   out_7572446057115886568[143] = 0;
   out_7572446057115886568[144] = 0;
   out_7572446057115886568[145] = 0;
   out_7572446057115886568[146] = 0;
   out_7572446057115886568[147] = 0;
   out_7572446057115886568[148] = 0;
   out_7572446057115886568[149] = 0;
   out_7572446057115886568[150] = 0;
   out_7572446057115886568[151] = 0;
   out_7572446057115886568[152] = 1;
   out_7572446057115886568[153] = 0;
   out_7572446057115886568[154] = 0;
   out_7572446057115886568[155] = 0;
   out_7572446057115886568[156] = 0;
   out_7572446057115886568[157] = 0;
   out_7572446057115886568[158] = 0;
   out_7572446057115886568[159] = 0;
   out_7572446057115886568[160] = 0;
   out_7572446057115886568[161] = 0;
   out_7572446057115886568[162] = 0;
   out_7572446057115886568[163] = 0;
   out_7572446057115886568[164] = 0;
   out_7572446057115886568[165] = 0;
   out_7572446057115886568[166] = 0;
   out_7572446057115886568[167] = 0;
   out_7572446057115886568[168] = 0;
   out_7572446057115886568[169] = 0;
   out_7572446057115886568[170] = 0;
   out_7572446057115886568[171] = 1;
   out_7572446057115886568[172] = 0;
   out_7572446057115886568[173] = 0;
   out_7572446057115886568[174] = 0;
   out_7572446057115886568[175] = 0;
   out_7572446057115886568[176] = 0;
   out_7572446057115886568[177] = 0;
   out_7572446057115886568[178] = 0;
   out_7572446057115886568[179] = 0;
   out_7572446057115886568[180] = 0;
   out_7572446057115886568[181] = 0;
   out_7572446057115886568[182] = 0;
   out_7572446057115886568[183] = 0;
   out_7572446057115886568[184] = 0;
   out_7572446057115886568[185] = 0;
   out_7572446057115886568[186] = 0;
   out_7572446057115886568[187] = 0;
   out_7572446057115886568[188] = 0;
   out_7572446057115886568[189] = 0;
   out_7572446057115886568[190] = 1;
   out_7572446057115886568[191] = 0;
   out_7572446057115886568[192] = 0;
   out_7572446057115886568[193] = 0;
   out_7572446057115886568[194] = 0;
   out_7572446057115886568[195] = 0;
   out_7572446057115886568[196] = 0;
   out_7572446057115886568[197] = 0;
   out_7572446057115886568[198] = 0;
   out_7572446057115886568[199] = 0;
   out_7572446057115886568[200] = 0;
   out_7572446057115886568[201] = 0;
   out_7572446057115886568[202] = 0;
   out_7572446057115886568[203] = 0;
   out_7572446057115886568[204] = 0;
   out_7572446057115886568[205] = 0;
   out_7572446057115886568[206] = 0;
   out_7572446057115886568[207] = 0;
   out_7572446057115886568[208] = 0;
   out_7572446057115886568[209] = 1;
   out_7572446057115886568[210] = 0;
   out_7572446057115886568[211] = 0;
   out_7572446057115886568[212] = 0;
   out_7572446057115886568[213] = 0;
   out_7572446057115886568[214] = 0;
   out_7572446057115886568[215] = 0;
   out_7572446057115886568[216] = 0;
   out_7572446057115886568[217] = 0;
   out_7572446057115886568[218] = 0;
   out_7572446057115886568[219] = 0;
   out_7572446057115886568[220] = 0;
   out_7572446057115886568[221] = 0;
   out_7572446057115886568[222] = 0;
   out_7572446057115886568[223] = 0;
   out_7572446057115886568[224] = 0;
   out_7572446057115886568[225] = 0;
   out_7572446057115886568[226] = 0;
   out_7572446057115886568[227] = 0;
   out_7572446057115886568[228] = 1;
   out_7572446057115886568[229] = 0;
   out_7572446057115886568[230] = 0;
   out_7572446057115886568[231] = 0;
   out_7572446057115886568[232] = 0;
   out_7572446057115886568[233] = 0;
   out_7572446057115886568[234] = 0;
   out_7572446057115886568[235] = 0;
   out_7572446057115886568[236] = 0;
   out_7572446057115886568[237] = 0;
   out_7572446057115886568[238] = 0;
   out_7572446057115886568[239] = 0;
   out_7572446057115886568[240] = 0;
   out_7572446057115886568[241] = 0;
   out_7572446057115886568[242] = 0;
   out_7572446057115886568[243] = 0;
   out_7572446057115886568[244] = 0;
   out_7572446057115886568[245] = 0;
   out_7572446057115886568[246] = 0;
   out_7572446057115886568[247] = 1;
   out_7572446057115886568[248] = 0;
   out_7572446057115886568[249] = 0;
   out_7572446057115886568[250] = 0;
   out_7572446057115886568[251] = 0;
   out_7572446057115886568[252] = 0;
   out_7572446057115886568[253] = 0;
   out_7572446057115886568[254] = 0;
   out_7572446057115886568[255] = 0;
   out_7572446057115886568[256] = 0;
   out_7572446057115886568[257] = 0;
   out_7572446057115886568[258] = 0;
   out_7572446057115886568[259] = 0;
   out_7572446057115886568[260] = 0;
   out_7572446057115886568[261] = 0;
   out_7572446057115886568[262] = 0;
   out_7572446057115886568[263] = 0;
   out_7572446057115886568[264] = 0;
   out_7572446057115886568[265] = 0;
   out_7572446057115886568[266] = 1;
   out_7572446057115886568[267] = 0;
   out_7572446057115886568[268] = 0;
   out_7572446057115886568[269] = 0;
   out_7572446057115886568[270] = 0;
   out_7572446057115886568[271] = 0;
   out_7572446057115886568[272] = 0;
   out_7572446057115886568[273] = 0;
   out_7572446057115886568[274] = 0;
   out_7572446057115886568[275] = 0;
   out_7572446057115886568[276] = 0;
   out_7572446057115886568[277] = 0;
   out_7572446057115886568[278] = 0;
   out_7572446057115886568[279] = 0;
   out_7572446057115886568[280] = 0;
   out_7572446057115886568[281] = 0;
   out_7572446057115886568[282] = 0;
   out_7572446057115886568[283] = 0;
   out_7572446057115886568[284] = 0;
   out_7572446057115886568[285] = 1;
   out_7572446057115886568[286] = 0;
   out_7572446057115886568[287] = 0;
   out_7572446057115886568[288] = 0;
   out_7572446057115886568[289] = 0;
   out_7572446057115886568[290] = 0;
   out_7572446057115886568[291] = 0;
   out_7572446057115886568[292] = 0;
   out_7572446057115886568[293] = 0;
   out_7572446057115886568[294] = 0;
   out_7572446057115886568[295] = 0;
   out_7572446057115886568[296] = 0;
   out_7572446057115886568[297] = 0;
   out_7572446057115886568[298] = 0;
   out_7572446057115886568[299] = 0;
   out_7572446057115886568[300] = 0;
   out_7572446057115886568[301] = 0;
   out_7572446057115886568[302] = 0;
   out_7572446057115886568[303] = 0;
   out_7572446057115886568[304] = 1;
   out_7572446057115886568[305] = 0;
   out_7572446057115886568[306] = 0;
   out_7572446057115886568[307] = 0;
   out_7572446057115886568[308] = 0;
   out_7572446057115886568[309] = 0;
   out_7572446057115886568[310] = 0;
   out_7572446057115886568[311] = 0;
   out_7572446057115886568[312] = 0;
   out_7572446057115886568[313] = 0;
   out_7572446057115886568[314] = 0;
   out_7572446057115886568[315] = 0;
   out_7572446057115886568[316] = 0;
   out_7572446057115886568[317] = 0;
   out_7572446057115886568[318] = 0;
   out_7572446057115886568[319] = 0;
   out_7572446057115886568[320] = 0;
   out_7572446057115886568[321] = 0;
   out_7572446057115886568[322] = 0;
   out_7572446057115886568[323] = 1;
}
void h_4(double *state, double *unused, double *out_2003156353488409837) {
   out_2003156353488409837[0] = state[6] + state[9];
   out_2003156353488409837[1] = state[7] + state[10];
   out_2003156353488409837[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_9153984278238564615) {
   out_9153984278238564615[0] = 0;
   out_9153984278238564615[1] = 0;
   out_9153984278238564615[2] = 0;
   out_9153984278238564615[3] = 0;
   out_9153984278238564615[4] = 0;
   out_9153984278238564615[5] = 0;
   out_9153984278238564615[6] = 1;
   out_9153984278238564615[7] = 0;
   out_9153984278238564615[8] = 0;
   out_9153984278238564615[9] = 1;
   out_9153984278238564615[10] = 0;
   out_9153984278238564615[11] = 0;
   out_9153984278238564615[12] = 0;
   out_9153984278238564615[13] = 0;
   out_9153984278238564615[14] = 0;
   out_9153984278238564615[15] = 0;
   out_9153984278238564615[16] = 0;
   out_9153984278238564615[17] = 0;
   out_9153984278238564615[18] = 0;
   out_9153984278238564615[19] = 0;
   out_9153984278238564615[20] = 0;
   out_9153984278238564615[21] = 0;
   out_9153984278238564615[22] = 0;
   out_9153984278238564615[23] = 0;
   out_9153984278238564615[24] = 0;
   out_9153984278238564615[25] = 1;
   out_9153984278238564615[26] = 0;
   out_9153984278238564615[27] = 0;
   out_9153984278238564615[28] = 1;
   out_9153984278238564615[29] = 0;
   out_9153984278238564615[30] = 0;
   out_9153984278238564615[31] = 0;
   out_9153984278238564615[32] = 0;
   out_9153984278238564615[33] = 0;
   out_9153984278238564615[34] = 0;
   out_9153984278238564615[35] = 0;
   out_9153984278238564615[36] = 0;
   out_9153984278238564615[37] = 0;
   out_9153984278238564615[38] = 0;
   out_9153984278238564615[39] = 0;
   out_9153984278238564615[40] = 0;
   out_9153984278238564615[41] = 0;
   out_9153984278238564615[42] = 0;
   out_9153984278238564615[43] = 0;
   out_9153984278238564615[44] = 1;
   out_9153984278238564615[45] = 0;
   out_9153984278238564615[46] = 0;
   out_9153984278238564615[47] = 1;
   out_9153984278238564615[48] = 0;
   out_9153984278238564615[49] = 0;
   out_9153984278238564615[50] = 0;
   out_9153984278238564615[51] = 0;
   out_9153984278238564615[52] = 0;
   out_9153984278238564615[53] = 0;
}
void h_10(double *state, double *unused, double *out_8299050468126391648) {
   out_8299050468126391648[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_8299050468126391648[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_8299050468126391648[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2268983315058168095) {
   out_2268983315058168095[0] = 0;
   out_2268983315058168095[1] = 9.8100000000000005*cos(state[1]);
   out_2268983315058168095[2] = 0;
   out_2268983315058168095[3] = 0;
   out_2268983315058168095[4] = -state[8];
   out_2268983315058168095[5] = state[7];
   out_2268983315058168095[6] = 0;
   out_2268983315058168095[7] = state[5];
   out_2268983315058168095[8] = -state[4];
   out_2268983315058168095[9] = 0;
   out_2268983315058168095[10] = 0;
   out_2268983315058168095[11] = 0;
   out_2268983315058168095[12] = 1;
   out_2268983315058168095[13] = 0;
   out_2268983315058168095[14] = 0;
   out_2268983315058168095[15] = 1;
   out_2268983315058168095[16] = 0;
   out_2268983315058168095[17] = 0;
   out_2268983315058168095[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2268983315058168095[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2268983315058168095[20] = 0;
   out_2268983315058168095[21] = state[8];
   out_2268983315058168095[22] = 0;
   out_2268983315058168095[23] = -state[6];
   out_2268983315058168095[24] = -state[5];
   out_2268983315058168095[25] = 0;
   out_2268983315058168095[26] = state[3];
   out_2268983315058168095[27] = 0;
   out_2268983315058168095[28] = 0;
   out_2268983315058168095[29] = 0;
   out_2268983315058168095[30] = 0;
   out_2268983315058168095[31] = 1;
   out_2268983315058168095[32] = 0;
   out_2268983315058168095[33] = 0;
   out_2268983315058168095[34] = 1;
   out_2268983315058168095[35] = 0;
   out_2268983315058168095[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2268983315058168095[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2268983315058168095[38] = 0;
   out_2268983315058168095[39] = -state[7];
   out_2268983315058168095[40] = state[6];
   out_2268983315058168095[41] = 0;
   out_2268983315058168095[42] = state[4];
   out_2268983315058168095[43] = -state[3];
   out_2268983315058168095[44] = 0;
   out_2268983315058168095[45] = 0;
   out_2268983315058168095[46] = 0;
   out_2268983315058168095[47] = 0;
   out_2268983315058168095[48] = 0;
   out_2268983315058168095[49] = 0;
   out_2268983315058168095[50] = 1;
   out_2268983315058168095[51] = 0;
   out_2268983315058168095[52] = 0;
   out_2268983315058168095[53] = 1;
}
void h_13(double *state, double *unused, double *out_8163970253337406046) {
   out_8163970253337406046[0] = state[3];
   out_8163970253337406046[1] = state[4];
   out_8163970253337406046[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1543353069921863686) {
   out_1543353069921863686[0] = 0;
   out_1543353069921863686[1] = 0;
   out_1543353069921863686[2] = 0;
   out_1543353069921863686[3] = 1;
   out_1543353069921863686[4] = 0;
   out_1543353069921863686[5] = 0;
   out_1543353069921863686[6] = 0;
   out_1543353069921863686[7] = 0;
   out_1543353069921863686[8] = 0;
   out_1543353069921863686[9] = 0;
   out_1543353069921863686[10] = 0;
   out_1543353069921863686[11] = 0;
   out_1543353069921863686[12] = 0;
   out_1543353069921863686[13] = 0;
   out_1543353069921863686[14] = 0;
   out_1543353069921863686[15] = 0;
   out_1543353069921863686[16] = 0;
   out_1543353069921863686[17] = 0;
   out_1543353069921863686[18] = 0;
   out_1543353069921863686[19] = 0;
   out_1543353069921863686[20] = 0;
   out_1543353069921863686[21] = 0;
   out_1543353069921863686[22] = 1;
   out_1543353069921863686[23] = 0;
   out_1543353069921863686[24] = 0;
   out_1543353069921863686[25] = 0;
   out_1543353069921863686[26] = 0;
   out_1543353069921863686[27] = 0;
   out_1543353069921863686[28] = 0;
   out_1543353069921863686[29] = 0;
   out_1543353069921863686[30] = 0;
   out_1543353069921863686[31] = 0;
   out_1543353069921863686[32] = 0;
   out_1543353069921863686[33] = 0;
   out_1543353069921863686[34] = 0;
   out_1543353069921863686[35] = 0;
   out_1543353069921863686[36] = 0;
   out_1543353069921863686[37] = 0;
   out_1543353069921863686[38] = 0;
   out_1543353069921863686[39] = 0;
   out_1543353069921863686[40] = 0;
   out_1543353069921863686[41] = 1;
   out_1543353069921863686[42] = 0;
   out_1543353069921863686[43] = 0;
   out_1543353069921863686[44] = 0;
   out_1543353069921863686[45] = 0;
   out_1543353069921863686[46] = 0;
   out_1543353069921863686[47] = 0;
   out_1543353069921863686[48] = 0;
   out_1543353069921863686[49] = 0;
   out_1543353069921863686[50] = 0;
   out_1543353069921863686[51] = 0;
   out_1543353069921863686[52] = 0;
   out_1543353069921863686[53] = 0;
}
void h_14(double *state, double *unused, double *out_7902513815616600364) {
   out_7902513815616600364[0] = state[6];
   out_7902513815616600364[1] = state[7];
   out_7902513815616600364[2] = state[8];
}
void H_14(double *state, double *unused, double *out_5190743421899080086) {
   out_5190743421899080086[0] = 0;
   out_5190743421899080086[1] = 0;
   out_5190743421899080086[2] = 0;
   out_5190743421899080086[3] = 0;
   out_5190743421899080086[4] = 0;
   out_5190743421899080086[5] = 0;
   out_5190743421899080086[6] = 1;
   out_5190743421899080086[7] = 0;
   out_5190743421899080086[8] = 0;
   out_5190743421899080086[9] = 0;
   out_5190743421899080086[10] = 0;
   out_5190743421899080086[11] = 0;
   out_5190743421899080086[12] = 0;
   out_5190743421899080086[13] = 0;
   out_5190743421899080086[14] = 0;
   out_5190743421899080086[15] = 0;
   out_5190743421899080086[16] = 0;
   out_5190743421899080086[17] = 0;
   out_5190743421899080086[18] = 0;
   out_5190743421899080086[19] = 0;
   out_5190743421899080086[20] = 0;
   out_5190743421899080086[21] = 0;
   out_5190743421899080086[22] = 0;
   out_5190743421899080086[23] = 0;
   out_5190743421899080086[24] = 0;
   out_5190743421899080086[25] = 1;
   out_5190743421899080086[26] = 0;
   out_5190743421899080086[27] = 0;
   out_5190743421899080086[28] = 0;
   out_5190743421899080086[29] = 0;
   out_5190743421899080086[30] = 0;
   out_5190743421899080086[31] = 0;
   out_5190743421899080086[32] = 0;
   out_5190743421899080086[33] = 0;
   out_5190743421899080086[34] = 0;
   out_5190743421899080086[35] = 0;
   out_5190743421899080086[36] = 0;
   out_5190743421899080086[37] = 0;
   out_5190743421899080086[38] = 0;
   out_5190743421899080086[39] = 0;
   out_5190743421899080086[40] = 0;
   out_5190743421899080086[41] = 0;
   out_5190743421899080086[42] = 0;
   out_5190743421899080086[43] = 0;
   out_5190743421899080086[44] = 1;
   out_5190743421899080086[45] = 0;
   out_5190743421899080086[46] = 0;
   out_5190743421899080086[47] = 0;
   out_5190743421899080086[48] = 0;
   out_5190743421899080086[49] = 0;
   out_5190743421899080086[50] = 0;
   out_5190743421899080086[51] = 0;
   out_5190743421899080086[52] = 0;
   out_5190743421899080086[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8743288361506485614) {
  err_fun(nom_x, delta_x, out_8743288361506485614);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7700232313042684193) {
  inv_err_fun(nom_x, true_x, out_7700232313042684193);
}
void pose_H_mod_fun(double *state, double *out_5879762199447615362) {
  H_mod_fun(state, out_5879762199447615362);
}
void pose_f_fun(double *state, double dt, double *out_9125558702662429027) {
  f_fun(state,  dt, out_9125558702662429027);
}
void pose_F_fun(double *state, double dt, double *out_7572446057115886568) {
  F_fun(state,  dt, out_7572446057115886568);
}
void pose_h_4(double *state, double *unused, double *out_2003156353488409837) {
  h_4(state, unused, out_2003156353488409837);
}
void pose_H_4(double *state, double *unused, double *out_9153984278238564615) {
  H_4(state, unused, out_9153984278238564615);
}
void pose_h_10(double *state, double *unused, double *out_8299050468126391648) {
  h_10(state, unused, out_8299050468126391648);
}
void pose_H_10(double *state, double *unused, double *out_2268983315058168095) {
  H_10(state, unused, out_2268983315058168095);
}
void pose_h_13(double *state, double *unused, double *out_8163970253337406046) {
  h_13(state, unused, out_8163970253337406046);
}
void pose_H_13(double *state, double *unused, double *out_1543353069921863686) {
  H_13(state, unused, out_1543353069921863686);
}
void pose_h_14(double *state, double *unused, double *out_7902513815616600364) {
  h_14(state, unused, out_7902513815616600364);
}
void pose_H_14(double *state, double *unused, double *out_5190743421899080086) {
  H_14(state, unused, out_5190743421899080086);
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
