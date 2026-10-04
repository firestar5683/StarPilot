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
void err_fun(double *nom_x, double *delta_x, double *out_6914886810623359485) {
   out_6914886810623359485[0] = delta_x[0] + nom_x[0];
   out_6914886810623359485[1] = delta_x[1] + nom_x[1];
   out_6914886810623359485[2] = delta_x[2] + nom_x[2];
   out_6914886810623359485[3] = delta_x[3] + nom_x[3];
   out_6914886810623359485[4] = delta_x[4] + nom_x[4];
   out_6914886810623359485[5] = delta_x[5] + nom_x[5];
   out_6914886810623359485[6] = delta_x[6] + nom_x[6];
   out_6914886810623359485[7] = delta_x[7] + nom_x[7];
   out_6914886810623359485[8] = delta_x[8] + nom_x[8];
   out_6914886810623359485[9] = delta_x[9] + nom_x[9];
   out_6914886810623359485[10] = delta_x[10] + nom_x[10];
   out_6914886810623359485[11] = delta_x[11] + nom_x[11];
   out_6914886810623359485[12] = delta_x[12] + nom_x[12];
   out_6914886810623359485[13] = delta_x[13] + nom_x[13];
   out_6914886810623359485[14] = delta_x[14] + nom_x[14];
   out_6914886810623359485[15] = delta_x[15] + nom_x[15];
   out_6914886810623359485[16] = delta_x[16] + nom_x[16];
   out_6914886810623359485[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1955170315450325036) {
   out_1955170315450325036[0] = -nom_x[0] + true_x[0];
   out_1955170315450325036[1] = -nom_x[1] + true_x[1];
   out_1955170315450325036[2] = -nom_x[2] + true_x[2];
   out_1955170315450325036[3] = -nom_x[3] + true_x[3];
   out_1955170315450325036[4] = -nom_x[4] + true_x[4];
   out_1955170315450325036[5] = -nom_x[5] + true_x[5];
   out_1955170315450325036[6] = -nom_x[6] + true_x[6];
   out_1955170315450325036[7] = -nom_x[7] + true_x[7];
   out_1955170315450325036[8] = -nom_x[8] + true_x[8];
   out_1955170315450325036[9] = -nom_x[9] + true_x[9];
   out_1955170315450325036[10] = -nom_x[10] + true_x[10];
   out_1955170315450325036[11] = -nom_x[11] + true_x[11];
   out_1955170315450325036[12] = -nom_x[12] + true_x[12];
   out_1955170315450325036[13] = -nom_x[13] + true_x[13];
   out_1955170315450325036[14] = -nom_x[14] + true_x[14];
   out_1955170315450325036[15] = -nom_x[15] + true_x[15];
   out_1955170315450325036[16] = -nom_x[16] + true_x[16];
   out_1955170315450325036[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6464744367615017758) {
   out_6464744367615017758[0] = 1.0;
   out_6464744367615017758[1] = 0.0;
   out_6464744367615017758[2] = 0.0;
   out_6464744367615017758[3] = 0.0;
   out_6464744367615017758[4] = 0.0;
   out_6464744367615017758[5] = 0.0;
   out_6464744367615017758[6] = 0.0;
   out_6464744367615017758[7] = 0.0;
   out_6464744367615017758[8] = 0.0;
   out_6464744367615017758[9] = 0.0;
   out_6464744367615017758[10] = 0.0;
   out_6464744367615017758[11] = 0.0;
   out_6464744367615017758[12] = 0.0;
   out_6464744367615017758[13] = 0.0;
   out_6464744367615017758[14] = 0.0;
   out_6464744367615017758[15] = 0.0;
   out_6464744367615017758[16] = 0.0;
   out_6464744367615017758[17] = 0.0;
   out_6464744367615017758[18] = 0.0;
   out_6464744367615017758[19] = 1.0;
   out_6464744367615017758[20] = 0.0;
   out_6464744367615017758[21] = 0.0;
   out_6464744367615017758[22] = 0.0;
   out_6464744367615017758[23] = 0.0;
   out_6464744367615017758[24] = 0.0;
   out_6464744367615017758[25] = 0.0;
   out_6464744367615017758[26] = 0.0;
   out_6464744367615017758[27] = 0.0;
   out_6464744367615017758[28] = 0.0;
   out_6464744367615017758[29] = 0.0;
   out_6464744367615017758[30] = 0.0;
   out_6464744367615017758[31] = 0.0;
   out_6464744367615017758[32] = 0.0;
   out_6464744367615017758[33] = 0.0;
   out_6464744367615017758[34] = 0.0;
   out_6464744367615017758[35] = 0.0;
   out_6464744367615017758[36] = 0.0;
   out_6464744367615017758[37] = 0.0;
   out_6464744367615017758[38] = 1.0;
   out_6464744367615017758[39] = 0.0;
   out_6464744367615017758[40] = 0.0;
   out_6464744367615017758[41] = 0.0;
   out_6464744367615017758[42] = 0.0;
   out_6464744367615017758[43] = 0.0;
   out_6464744367615017758[44] = 0.0;
   out_6464744367615017758[45] = 0.0;
   out_6464744367615017758[46] = 0.0;
   out_6464744367615017758[47] = 0.0;
   out_6464744367615017758[48] = 0.0;
   out_6464744367615017758[49] = 0.0;
   out_6464744367615017758[50] = 0.0;
   out_6464744367615017758[51] = 0.0;
   out_6464744367615017758[52] = 0.0;
   out_6464744367615017758[53] = 0.0;
   out_6464744367615017758[54] = 0.0;
   out_6464744367615017758[55] = 0.0;
   out_6464744367615017758[56] = 0.0;
   out_6464744367615017758[57] = 1.0;
   out_6464744367615017758[58] = 0.0;
   out_6464744367615017758[59] = 0.0;
   out_6464744367615017758[60] = 0.0;
   out_6464744367615017758[61] = 0.0;
   out_6464744367615017758[62] = 0.0;
   out_6464744367615017758[63] = 0.0;
   out_6464744367615017758[64] = 0.0;
   out_6464744367615017758[65] = 0.0;
   out_6464744367615017758[66] = 0.0;
   out_6464744367615017758[67] = 0.0;
   out_6464744367615017758[68] = 0.0;
   out_6464744367615017758[69] = 0.0;
   out_6464744367615017758[70] = 0.0;
   out_6464744367615017758[71] = 0.0;
   out_6464744367615017758[72] = 0.0;
   out_6464744367615017758[73] = 0.0;
   out_6464744367615017758[74] = 0.0;
   out_6464744367615017758[75] = 0.0;
   out_6464744367615017758[76] = 1.0;
   out_6464744367615017758[77] = 0.0;
   out_6464744367615017758[78] = 0.0;
   out_6464744367615017758[79] = 0.0;
   out_6464744367615017758[80] = 0.0;
   out_6464744367615017758[81] = 0.0;
   out_6464744367615017758[82] = 0.0;
   out_6464744367615017758[83] = 0.0;
   out_6464744367615017758[84] = 0.0;
   out_6464744367615017758[85] = 0.0;
   out_6464744367615017758[86] = 0.0;
   out_6464744367615017758[87] = 0.0;
   out_6464744367615017758[88] = 0.0;
   out_6464744367615017758[89] = 0.0;
   out_6464744367615017758[90] = 0.0;
   out_6464744367615017758[91] = 0.0;
   out_6464744367615017758[92] = 0.0;
   out_6464744367615017758[93] = 0.0;
   out_6464744367615017758[94] = 0.0;
   out_6464744367615017758[95] = 1.0;
   out_6464744367615017758[96] = 0.0;
   out_6464744367615017758[97] = 0.0;
   out_6464744367615017758[98] = 0.0;
   out_6464744367615017758[99] = 0.0;
   out_6464744367615017758[100] = 0.0;
   out_6464744367615017758[101] = 0.0;
   out_6464744367615017758[102] = 0.0;
   out_6464744367615017758[103] = 0.0;
   out_6464744367615017758[104] = 0.0;
   out_6464744367615017758[105] = 0.0;
   out_6464744367615017758[106] = 0.0;
   out_6464744367615017758[107] = 0.0;
   out_6464744367615017758[108] = 0.0;
   out_6464744367615017758[109] = 0.0;
   out_6464744367615017758[110] = 0.0;
   out_6464744367615017758[111] = 0.0;
   out_6464744367615017758[112] = 0.0;
   out_6464744367615017758[113] = 0.0;
   out_6464744367615017758[114] = 1.0;
   out_6464744367615017758[115] = 0.0;
   out_6464744367615017758[116] = 0.0;
   out_6464744367615017758[117] = 0.0;
   out_6464744367615017758[118] = 0.0;
   out_6464744367615017758[119] = 0.0;
   out_6464744367615017758[120] = 0.0;
   out_6464744367615017758[121] = 0.0;
   out_6464744367615017758[122] = 0.0;
   out_6464744367615017758[123] = 0.0;
   out_6464744367615017758[124] = 0.0;
   out_6464744367615017758[125] = 0.0;
   out_6464744367615017758[126] = 0.0;
   out_6464744367615017758[127] = 0.0;
   out_6464744367615017758[128] = 0.0;
   out_6464744367615017758[129] = 0.0;
   out_6464744367615017758[130] = 0.0;
   out_6464744367615017758[131] = 0.0;
   out_6464744367615017758[132] = 0.0;
   out_6464744367615017758[133] = 1.0;
   out_6464744367615017758[134] = 0.0;
   out_6464744367615017758[135] = 0.0;
   out_6464744367615017758[136] = 0.0;
   out_6464744367615017758[137] = 0.0;
   out_6464744367615017758[138] = 0.0;
   out_6464744367615017758[139] = 0.0;
   out_6464744367615017758[140] = 0.0;
   out_6464744367615017758[141] = 0.0;
   out_6464744367615017758[142] = 0.0;
   out_6464744367615017758[143] = 0.0;
   out_6464744367615017758[144] = 0.0;
   out_6464744367615017758[145] = 0.0;
   out_6464744367615017758[146] = 0.0;
   out_6464744367615017758[147] = 0.0;
   out_6464744367615017758[148] = 0.0;
   out_6464744367615017758[149] = 0.0;
   out_6464744367615017758[150] = 0.0;
   out_6464744367615017758[151] = 0.0;
   out_6464744367615017758[152] = 1.0;
   out_6464744367615017758[153] = 0.0;
   out_6464744367615017758[154] = 0.0;
   out_6464744367615017758[155] = 0.0;
   out_6464744367615017758[156] = 0.0;
   out_6464744367615017758[157] = 0.0;
   out_6464744367615017758[158] = 0.0;
   out_6464744367615017758[159] = 0.0;
   out_6464744367615017758[160] = 0.0;
   out_6464744367615017758[161] = 0.0;
   out_6464744367615017758[162] = 0.0;
   out_6464744367615017758[163] = 0.0;
   out_6464744367615017758[164] = 0.0;
   out_6464744367615017758[165] = 0.0;
   out_6464744367615017758[166] = 0.0;
   out_6464744367615017758[167] = 0.0;
   out_6464744367615017758[168] = 0.0;
   out_6464744367615017758[169] = 0.0;
   out_6464744367615017758[170] = 0.0;
   out_6464744367615017758[171] = 1.0;
   out_6464744367615017758[172] = 0.0;
   out_6464744367615017758[173] = 0.0;
   out_6464744367615017758[174] = 0.0;
   out_6464744367615017758[175] = 0.0;
   out_6464744367615017758[176] = 0.0;
   out_6464744367615017758[177] = 0.0;
   out_6464744367615017758[178] = 0.0;
   out_6464744367615017758[179] = 0.0;
   out_6464744367615017758[180] = 0.0;
   out_6464744367615017758[181] = 0.0;
   out_6464744367615017758[182] = 0.0;
   out_6464744367615017758[183] = 0.0;
   out_6464744367615017758[184] = 0.0;
   out_6464744367615017758[185] = 0.0;
   out_6464744367615017758[186] = 0.0;
   out_6464744367615017758[187] = 0.0;
   out_6464744367615017758[188] = 0.0;
   out_6464744367615017758[189] = 0.0;
   out_6464744367615017758[190] = 1.0;
   out_6464744367615017758[191] = 0.0;
   out_6464744367615017758[192] = 0.0;
   out_6464744367615017758[193] = 0.0;
   out_6464744367615017758[194] = 0.0;
   out_6464744367615017758[195] = 0.0;
   out_6464744367615017758[196] = 0.0;
   out_6464744367615017758[197] = 0.0;
   out_6464744367615017758[198] = 0.0;
   out_6464744367615017758[199] = 0.0;
   out_6464744367615017758[200] = 0.0;
   out_6464744367615017758[201] = 0.0;
   out_6464744367615017758[202] = 0.0;
   out_6464744367615017758[203] = 0.0;
   out_6464744367615017758[204] = 0.0;
   out_6464744367615017758[205] = 0.0;
   out_6464744367615017758[206] = 0.0;
   out_6464744367615017758[207] = 0.0;
   out_6464744367615017758[208] = 0.0;
   out_6464744367615017758[209] = 1.0;
   out_6464744367615017758[210] = 0.0;
   out_6464744367615017758[211] = 0.0;
   out_6464744367615017758[212] = 0.0;
   out_6464744367615017758[213] = 0.0;
   out_6464744367615017758[214] = 0.0;
   out_6464744367615017758[215] = 0.0;
   out_6464744367615017758[216] = 0.0;
   out_6464744367615017758[217] = 0.0;
   out_6464744367615017758[218] = 0.0;
   out_6464744367615017758[219] = 0.0;
   out_6464744367615017758[220] = 0.0;
   out_6464744367615017758[221] = 0.0;
   out_6464744367615017758[222] = 0.0;
   out_6464744367615017758[223] = 0.0;
   out_6464744367615017758[224] = 0.0;
   out_6464744367615017758[225] = 0.0;
   out_6464744367615017758[226] = 0.0;
   out_6464744367615017758[227] = 0.0;
   out_6464744367615017758[228] = 1.0;
   out_6464744367615017758[229] = 0.0;
   out_6464744367615017758[230] = 0.0;
   out_6464744367615017758[231] = 0.0;
   out_6464744367615017758[232] = 0.0;
   out_6464744367615017758[233] = 0.0;
   out_6464744367615017758[234] = 0.0;
   out_6464744367615017758[235] = 0.0;
   out_6464744367615017758[236] = 0.0;
   out_6464744367615017758[237] = 0.0;
   out_6464744367615017758[238] = 0.0;
   out_6464744367615017758[239] = 0.0;
   out_6464744367615017758[240] = 0.0;
   out_6464744367615017758[241] = 0.0;
   out_6464744367615017758[242] = 0.0;
   out_6464744367615017758[243] = 0.0;
   out_6464744367615017758[244] = 0.0;
   out_6464744367615017758[245] = 0.0;
   out_6464744367615017758[246] = 0.0;
   out_6464744367615017758[247] = 1.0;
   out_6464744367615017758[248] = 0.0;
   out_6464744367615017758[249] = 0.0;
   out_6464744367615017758[250] = 0.0;
   out_6464744367615017758[251] = 0.0;
   out_6464744367615017758[252] = 0.0;
   out_6464744367615017758[253] = 0.0;
   out_6464744367615017758[254] = 0.0;
   out_6464744367615017758[255] = 0.0;
   out_6464744367615017758[256] = 0.0;
   out_6464744367615017758[257] = 0.0;
   out_6464744367615017758[258] = 0.0;
   out_6464744367615017758[259] = 0.0;
   out_6464744367615017758[260] = 0.0;
   out_6464744367615017758[261] = 0.0;
   out_6464744367615017758[262] = 0.0;
   out_6464744367615017758[263] = 0.0;
   out_6464744367615017758[264] = 0.0;
   out_6464744367615017758[265] = 0.0;
   out_6464744367615017758[266] = 1.0;
   out_6464744367615017758[267] = 0.0;
   out_6464744367615017758[268] = 0.0;
   out_6464744367615017758[269] = 0.0;
   out_6464744367615017758[270] = 0.0;
   out_6464744367615017758[271] = 0.0;
   out_6464744367615017758[272] = 0.0;
   out_6464744367615017758[273] = 0.0;
   out_6464744367615017758[274] = 0.0;
   out_6464744367615017758[275] = 0.0;
   out_6464744367615017758[276] = 0.0;
   out_6464744367615017758[277] = 0.0;
   out_6464744367615017758[278] = 0.0;
   out_6464744367615017758[279] = 0.0;
   out_6464744367615017758[280] = 0.0;
   out_6464744367615017758[281] = 0.0;
   out_6464744367615017758[282] = 0.0;
   out_6464744367615017758[283] = 0.0;
   out_6464744367615017758[284] = 0.0;
   out_6464744367615017758[285] = 1.0;
   out_6464744367615017758[286] = 0.0;
   out_6464744367615017758[287] = 0.0;
   out_6464744367615017758[288] = 0.0;
   out_6464744367615017758[289] = 0.0;
   out_6464744367615017758[290] = 0.0;
   out_6464744367615017758[291] = 0.0;
   out_6464744367615017758[292] = 0.0;
   out_6464744367615017758[293] = 0.0;
   out_6464744367615017758[294] = 0.0;
   out_6464744367615017758[295] = 0.0;
   out_6464744367615017758[296] = 0.0;
   out_6464744367615017758[297] = 0.0;
   out_6464744367615017758[298] = 0.0;
   out_6464744367615017758[299] = 0.0;
   out_6464744367615017758[300] = 0.0;
   out_6464744367615017758[301] = 0.0;
   out_6464744367615017758[302] = 0.0;
   out_6464744367615017758[303] = 0.0;
   out_6464744367615017758[304] = 1.0;
   out_6464744367615017758[305] = 0.0;
   out_6464744367615017758[306] = 0.0;
   out_6464744367615017758[307] = 0.0;
   out_6464744367615017758[308] = 0.0;
   out_6464744367615017758[309] = 0.0;
   out_6464744367615017758[310] = 0.0;
   out_6464744367615017758[311] = 0.0;
   out_6464744367615017758[312] = 0.0;
   out_6464744367615017758[313] = 0.0;
   out_6464744367615017758[314] = 0.0;
   out_6464744367615017758[315] = 0.0;
   out_6464744367615017758[316] = 0.0;
   out_6464744367615017758[317] = 0.0;
   out_6464744367615017758[318] = 0.0;
   out_6464744367615017758[319] = 0.0;
   out_6464744367615017758[320] = 0.0;
   out_6464744367615017758[321] = 0.0;
   out_6464744367615017758[322] = 0.0;
   out_6464744367615017758[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_843490903718422953) {
   out_843490903718422953[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_843490903718422953[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_843490903718422953[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_843490903718422953[3] = dt*state[12] + state[3];
   out_843490903718422953[4] = dt*state[13] + state[4];
   out_843490903718422953[5] = dt*state[14] + state[5];
   out_843490903718422953[6] = state[6];
   out_843490903718422953[7] = state[7];
   out_843490903718422953[8] = state[8];
   out_843490903718422953[9] = state[9];
   out_843490903718422953[10] = state[10];
   out_843490903718422953[11] = state[11];
   out_843490903718422953[12] = state[12];
   out_843490903718422953[13] = state[13];
   out_843490903718422953[14] = state[14];
   out_843490903718422953[15] = state[15];
   out_843490903718422953[16] = state[16];
   out_843490903718422953[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8919071219298160156) {
   out_8919071219298160156[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8919071219298160156[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8919071219298160156[2] = 0;
   out_8919071219298160156[3] = 0;
   out_8919071219298160156[4] = 0;
   out_8919071219298160156[5] = 0;
   out_8919071219298160156[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8919071219298160156[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8919071219298160156[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8919071219298160156[9] = 0;
   out_8919071219298160156[10] = 0;
   out_8919071219298160156[11] = 0;
   out_8919071219298160156[12] = 0;
   out_8919071219298160156[13] = 0;
   out_8919071219298160156[14] = 0;
   out_8919071219298160156[15] = 0;
   out_8919071219298160156[16] = 0;
   out_8919071219298160156[17] = 0;
   out_8919071219298160156[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8919071219298160156[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8919071219298160156[20] = 0;
   out_8919071219298160156[21] = 0;
   out_8919071219298160156[22] = 0;
   out_8919071219298160156[23] = 0;
   out_8919071219298160156[24] = 0;
   out_8919071219298160156[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8919071219298160156[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8919071219298160156[27] = 0;
   out_8919071219298160156[28] = 0;
   out_8919071219298160156[29] = 0;
   out_8919071219298160156[30] = 0;
   out_8919071219298160156[31] = 0;
   out_8919071219298160156[32] = 0;
   out_8919071219298160156[33] = 0;
   out_8919071219298160156[34] = 0;
   out_8919071219298160156[35] = 0;
   out_8919071219298160156[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8919071219298160156[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8919071219298160156[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8919071219298160156[39] = 0;
   out_8919071219298160156[40] = 0;
   out_8919071219298160156[41] = 0;
   out_8919071219298160156[42] = 0;
   out_8919071219298160156[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8919071219298160156[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8919071219298160156[45] = 0;
   out_8919071219298160156[46] = 0;
   out_8919071219298160156[47] = 0;
   out_8919071219298160156[48] = 0;
   out_8919071219298160156[49] = 0;
   out_8919071219298160156[50] = 0;
   out_8919071219298160156[51] = 0;
   out_8919071219298160156[52] = 0;
   out_8919071219298160156[53] = 0;
   out_8919071219298160156[54] = 0;
   out_8919071219298160156[55] = 0;
   out_8919071219298160156[56] = 0;
   out_8919071219298160156[57] = 1;
   out_8919071219298160156[58] = 0;
   out_8919071219298160156[59] = 0;
   out_8919071219298160156[60] = 0;
   out_8919071219298160156[61] = 0;
   out_8919071219298160156[62] = 0;
   out_8919071219298160156[63] = 0;
   out_8919071219298160156[64] = 0;
   out_8919071219298160156[65] = 0;
   out_8919071219298160156[66] = dt;
   out_8919071219298160156[67] = 0;
   out_8919071219298160156[68] = 0;
   out_8919071219298160156[69] = 0;
   out_8919071219298160156[70] = 0;
   out_8919071219298160156[71] = 0;
   out_8919071219298160156[72] = 0;
   out_8919071219298160156[73] = 0;
   out_8919071219298160156[74] = 0;
   out_8919071219298160156[75] = 0;
   out_8919071219298160156[76] = 1;
   out_8919071219298160156[77] = 0;
   out_8919071219298160156[78] = 0;
   out_8919071219298160156[79] = 0;
   out_8919071219298160156[80] = 0;
   out_8919071219298160156[81] = 0;
   out_8919071219298160156[82] = 0;
   out_8919071219298160156[83] = 0;
   out_8919071219298160156[84] = 0;
   out_8919071219298160156[85] = dt;
   out_8919071219298160156[86] = 0;
   out_8919071219298160156[87] = 0;
   out_8919071219298160156[88] = 0;
   out_8919071219298160156[89] = 0;
   out_8919071219298160156[90] = 0;
   out_8919071219298160156[91] = 0;
   out_8919071219298160156[92] = 0;
   out_8919071219298160156[93] = 0;
   out_8919071219298160156[94] = 0;
   out_8919071219298160156[95] = 1;
   out_8919071219298160156[96] = 0;
   out_8919071219298160156[97] = 0;
   out_8919071219298160156[98] = 0;
   out_8919071219298160156[99] = 0;
   out_8919071219298160156[100] = 0;
   out_8919071219298160156[101] = 0;
   out_8919071219298160156[102] = 0;
   out_8919071219298160156[103] = 0;
   out_8919071219298160156[104] = dt;
   out_8919071219298160156[105] = 0;
   out_8919071219298160156[106] = 0;
   out_8919071219298160156[107] = 0;
   out_8919071219298160156[108] = 0;
   out_8919071219298160156[109] = 0;
   out_8919071219298160156[110] = 0;
   out_8919071219298160156[111] = 0;
   out_8919071219298160156[112] = 0;
   out_8919071219298160156[113] = 0;
   out_8919071219298160156[114] = 1;
   out_8919071219298160156[115] = 0;
   out_8919071219298160156[116] = 0;
   out_8919071219298160156[117] = 0;
   out_8919071219298160156[118] = 0;
   out_8919071219298160156[119] = 0;
   out_8919071219298160156[120] = 0;
   out_8919071219298160156[121] = 0;
   out_8919071219298160156[122] = 0;
   out_8919071219298160156[123] = 0;
   out_8919071219298160156[124] = 0;
   out_8919071219298160156[125] = 0;
   out_8919071219298160156[126] = 0;
   out_8919071219298160156[127] = 0;
   out_8919071219298160156[128] = 0;
   out_8919071219298160156[129] = 0;
   out_8919071219298160156[130] = 0;
   out_8919071219298160156[131] = 0;
   out_8919071219298160156[132] = 0;
   out_8919071219298160156[133] = 1;
   out_8919071219298160156[134] = 0;
   out_8919071219298160156[135] = 0;
   out_8919071219298160156[136] = 0;
   out_8919071219298160156[137] = 0;
   out_8919071219298160156[138] = 0;
   out_8919071219298160156[139] = 0;
   out_8919071219298160156[140] = 0;
   out_8919071219298160156[141] = 0;
   out_8919071219298160156[142] = 0;
   out_8919071219298160156[143] = 0;
   out_8919071219298160156[144] = 0;
   out_8919071219298160156[145] = 0;
   out_8919071219298160156[146] = 0;
   out_8919071219298160156[147] = 0;
   out_8919071219298160156[148] = 0;
   out_8919071219298160156[149] = 0;
   out_8919071219298160156[150] = 0;
   out_8919071219298160156[151] = 0;
   out_8919071219298160156[152] = 1;
   out_8919071219298160156[153] = 0;
   out_8919071219298160156[154] = 0;
   out_8919071219298160156[155] = 0;
   out_8919071219298160156[156] = 0;
   out_8919071219298160156[157] = 0;
   out_8919071219298160156[158] = 0;
   out_8919071219298160156[159] = 0;
   out_8919071219298160156[160] = 0;
   out_8919071219298160156[161] = 0;
   out_8919071219298160156[162] = 0;
   out_8919071219298160156[163] = 0;
   out_8919071219298160156[164] = 0;
   out_8919071219298160156[165] = 0;
   out_8919071219298160156[166] = 0;
   out_8919071219298160156[167] = 0;
   out_8919071219298160156[168] = 0;
   out_8919071219298160156[169] = 0;
   out_8919071219298160156[170] = 0;
   out_8919071219298160156[171] = 1;
   out_8919071219298160156[172] = 0;
   out_8919071219298160156[173] = 0;
   out_8919071219298160156[174] = 0;
   out_8919071219298160156[175] = 0;
   out_8919071219298160156[176] = 0;
   out_8919071219298160156[177] = 0;
   out_8919071219298160156[178] = 0;
   out_8919071219298160156[179] = 0;
   out_8919071219298160156[180] = 0;
   out_8919071219298160156[181] = 0;
   out_8919071219298160156[182] = 0;
   out_8919071219298160156[183] = 0;
   out_8919071219298160156[184] = 0;
   out_8919071219298160156[185] = 0;
   out_8919071219298160156[186] = 0;
   out_8919071219298160156[187] = 0;
   out_8919071219298160156[188] = 0;
   out_8919071219298160156[189] = 0;
   out_8919071219298160156[190] = 1;
   out_8919071219298160156[191] = 0;
   out_8919071219298160156[192] = 0;
   out_8919071219298160156[193] = 0;
   out_8919071219298160156[194] = 0;
   out_8919071219298160156[195] = 0;
   out_8919071219298160156[196] = 0;
   out_8919071219298160156[197] = 0;
   out_8919071219298160156[198] = 0;
   out_8919071219298160156[199] = 0;
   out_8919071219298160156[200] = 0;
   out_8919071219298160156[201] = 0;
   out_8919071219298160156[202] = 0;
   out_8919071219298160156[203] = 0;
   out_8919071219298160156[204] = 0;
   out_8919071219298160156[205] = 0;
   out_8919071219298160156[206] = 0;
   out_8919071219298160156[207] = 0;
   out_8919071219298160156[208] = 0;
   out_8919071219298160156[209] = 1;
   out_8919071219298160156[210] = 0;
   out_8919071219298160156[211] = 0;
   out_8919071219298160156[212] = 0;
   out_8919071219298160156[213] = 0;
   out_8919071219298160156[214] = 0;
   out_8919071219298160156[215] = 0;
   out_8919071219298160156[216] = 0;
   out_8919071219298160156[217] = 0;
   out_8919071219298160156[218] = 0;
   out_8919071219298160156[219] = 0;
   out_8919071219298160156[220] = 0;
   out_8919071219298160156[221] = 0;
   out_8919071219298160156[222] = 0;
   out_8919071219298160156[223] = 0;
   out_8919071219298160156[224] = 0;
   out_8919071219298160156[225] = 0;
   out_8919071219298160156[226] = 0;
   out_8919071219298160156[227] = 0;
   out_8919071219298160156[228] = 1;
   out_8919071219298160156[229] = 0;
   out_8919071219298160156[230] = 0;
   out_8919071219298160156[231] = 0;
   out_8919071219298160156[232] = 0;
   out_8919071219298160156[233] = 0;
   out_8919071219298160156[234] = 0;
   out_8919071219298160156[235] = 0;
   out_8919071219298160156[236] = 0;
   out_8919071219298160156[237] = 0;
   out_8919071219298160156[238] = 0;
   out_8919071219298160156[239] = 0;
   out_8919071219298160156[240] = 0;
   out_8919071219298160156[241] = 0;
   out_8919071219298160156[242] = 0;
   out_8919071219298160156[243] = 0;
   out_8919071219298160156[244] = 0;
   out_8919071219298160156[245] = 0;
   out_8919071219298160156[246] = 0;
   out_8919071219298160156[247] = 1;
   out_8919071219298160156[248] = 0;
   out_8919071219298160156[249] = 0;
   out_8919071219298160156[250] = 0;
   out_8919071219298160156[251] = 0;
   out_8919071219298160156[252] = 0;
   out_8919071219298160156[253] = 0;
   out_8919071219298160156[254] = 0;
   out_8919071219298160156[255] = 0;
   out_8919071219298160156[256] = 0;
   out_8919071219298160156[257] = 0;
   out_8919071219298160156[258] = 0;
   out_8919071219298160156[259] = 0;
   out_8919071219298160156[260] = 0;
   out_8919071219298160156[261] = 0;
   out_8919071219298160156[262] = 0;
   out_8919071219298160156[263] = 0;
   out_8919071219298160156[264] = 0;
   out_8919071219298160156[265] = 0;
   out_8919071219298160156[266] = 1;
   out_8919071219298160156[267] = 0;
   out_8919071219298160156[268] = 0;
   out_8919071219298160156[269] = 0;
   out_8919071219298160156[270] = 0;
   out_8919071219298160156[271] = 0;
   out_8919071219298160156[272] = 0;
   out_8919071219298160156[273] = 0;
   out_8919071219298160156[274] = 0;
   out_8919071219298160156[275] = 0;
   out_8919071219298160156[276] = 0;
   out_8919071219298160156[277] = 0;
   out_8919071219298160156[278] = 0;
   out_8919071219298160156[279] = 0;
   out_8919071219298160156[280] = 0;
   out_8919071219298160156[281] = 0;
   out_8919071219298160156[282] = 0;
   out_8919071219298160156[283] = 0;
   out_8919071219298160156[284] = 0;
   out_8919071219298160156[285] = 1;
   out_8919071219298160156[286] = 0;
   out_8919071219298160156[287] = 0;
   out_8919071219298160156[288] = 0;
   out_8919071219298160156[289] = 0;
   out_8919071219298160156[290] = 0;
   out_8919071219298160156[291] = 0;
   out_8919071219298160156[292] = 0;
   out_8919071219298160156[293] = 0;
   out_8919071219298160156[294] = 0;
   out_8919071219298160156[295] = 0;
   out_8919071219298160156[296] = 0;
   out_8919071219298160156[297] = 0;
   out_8919071219298160156[298] = 0;
   out_8919071219298160156[299] = 0;
   out_8919071219298160156[300] = 0;
   out_8919071219298160156[301] = 0;
   out_8919071219298160156[302] = 0;
   out_8919071219298160156[303] = 0;
   out_8919071219298160156[304] = 1;
   out_8919071219298160156[305] = 0;
   out_8919071219298160156[306] = 0;
   out_8919071219298160156[307] = 0;
   out_8919071219298160156[308] = 0;
   out_8919071219298160156[309] = 0;
   out_8919071219298160156[310] = 0;
   out_8919071219298160156[311] = 0;
   out_8919071219298160156[312] = 0;
   out_8919071219298160156[313] = 0;
   out_8919071219298160156[314] = 0;
   out_8919071219298160156[315] = 0;
   out_8919071219298160156[316] = 0;
   out_8919071219298160156[317] = 0;
   out_8919071219298160156[318] = 0;
   out_8919071219298160156[319] = 0;
   out_8919071219298160156[320] = 0;
   out_8919071219298160156[321] = 0;
   out_8919071219298160156[322] = 0;
   out_8919071219298160156[323] = 1;
}
void h_4(double *state, double *unused, double *out_173130356706362345) {
   out_173130356706362345[0] = state[6] + state[9];
   out_173130356706362345[1] = state[7] + state[10];
   out_173130356706362345[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3243803474011544720) {
   out_3243803474011544720[0] = 0;
   out_3243803474011544720[1] = 0;
   out_3243803474011544720[2] = 0;
   out_3243803474011544720[3] = 0;
   out_3243803474011544720[4] = 0;
   out_3243803474011544720[5] = 0;
   out_3243803474011544720[6] = 1;
   out_3243803474011544720[7] = 0;
   out_3243803474011544720[8] = 0;
   out_3243803474011544720[9] = 1;
   out_3243803474011544720[10] = 0;
   out_3243803474011544720[11] = 0;
   out_3243803474011544720[12] = 0;
   out_3243803474011544720[13] = 0;
   out_3243803474011544720[14] = 0;
   out_3243803474011544720[15] = 0;
   out_3243803474011544720[16] = 0;
   out_3243803474011544720[17] = 0;
   out_3243803474011544720[18] = 0;
   out_3243803474011544720[19] = 0;
   out_3243803474011544720[20] = 0;
   out_3243803474011544720[21] = 0;
   out_3243803474011544720[22] = 0;
   out_3243803474011544720[23] = 0;
   out_3243803474011544720[24] = 0;
   out_3243803474011544720[25] = 1;
   out_3243803474011544720[26] = 0;
   out_3243803474011544720[27] = 0;
   out_3243803474011544720[28] = 1;
   out_3243803474011544720[29] = 0;
   out_3243803474011544720[30] = 0;
   out_3243803474011544720[31] = 0;
   out_3243803474011544720[32] = 0;
   out_3243803474011544720[33] = 0;
   out_3243803474011544720[34] = 0;
   out_3243803474011544720[35] = 0;
   out_3243803474011544720[36] = 0;
   out_3243803474011544720[37] = 0;
   out_3243803474011544720[38] = 0;
   out_3243803474011544720[39] = 0;
   out_3243803474011544720[40] = 0;
   out_3243803474011544720[41] = 0;
   out_3243803474011544720[42] = 0;
   out_3243803474011544720[43] = 0;
   out_3243803474011544720[44] = 1;
   out_3243803474011544720[45] = 0;
   out_3243803474011544720[46] = 0;
   out_3243803474011544720[47] = 1;
   out_3243803474011544720[48] = 0;
   out_3243803474011544720[49] = 0;
   out_3243803474011544720[50] = 0;
   out_3243803474011544720[51] = 0;
   out_3243803474011544720[52] = 0;
   out_3243803474011544720[53] = 0;
}
void h_10(double *state, double *unused, double *out_3220967759669022070) {
   out_3220967759669022070[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3220967759669022070[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3220967759669022070[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7792322668041282962) {
   out_7792322668041282962[0] = 0;
   out_7792322668041282962[1] = 9.8100000000000005*cos(state[1]);
   out_7792322668041282962[2] = 0;
   out_7792322668041282962[3] = 0;
   out_7792322668041282962[4] = -state[8];
   out_7792322668041282962[5] = state[7];
   out_7792322668041282962[6] = 0;
   out_7792322668041282962[7] = state[5];
   out_7792322668041282962[8] = -state[4];
   out_7792322668041282962[9] = 0;
   out_7792322668041282962[10] = 0;
   out_7792322668041282962[11] = 0;
   out_7792322668041282962[12] = 1;
   out_7792322668041282962[13] = 0;
   out_7792322668041282962[14] = 0;
   out_7792322668041282962[15] = 1;
   out_7792322668041282962[16] = 0;
   out_7792322668041282962[17] = 0;
   out_7792322668041282962[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7792322668041282962[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7792322668041282962[20] = 0;
   out_7792322668041282962[21] = state[8];
   out_7792322668041282962[22] = 0;
   out_7792322668041282962[23] = -state[6];
   out_7792322668041282962[24] = -state[5];
   out_7792322668041282962[25] = 0;
   out_7792322668041282962[26] = state[3];
   out_7792322668041282962[27] = 0;
   out_7792322668041282962[28] = 0;
   out_7792322668041282962[29] = 0;
   out_7792322668041282962[30] = 0;
   out_7792322668041282962[31] = 1;
   out_7792322668041282962[32] = 0;
   out_7792322668041282962[33] = 0;
   out_7792322668041282962[34] = 1;
   out_7792322668041282962[35] = 0;
   out_7792322668041282962[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7792322668041282962[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7792322668041282962[38] = 0;
   out_7792322668041282962[39] = -state[7];
   out_7792322668041282962[40] = state[6];
   out_7792322668041282962[41] = 0;
   out_7792322668041282962[42] = state[4];
   out_7792322668041282962[43] = -state[3];
   out_7792322668041282962[44] = 0;
   out_7792322668041282962[45] = 0;
   out_7792322668041282962[46] = 0;
   out_7792322668041282962[47] = 0;
   out_7792322668041282962[48] = 0;
   out_7792322668041282962[49] = 0;
   out_7792322668041282962[50] = 1;
   out_7792322668041282962[51] = 0;
   out_7792322668041282962[52] = 0;
   out_7792322668041282962[53] = 1;
}
void h_13(double *state, double *unused, double *out_5680375753611876010) {
   out_5680375753611876010[0] = state[3];
   out_5680375753611876010[1] = state[4];
   out_5680375753611876010[2] = state[5];
}
void H_13(double *state, double *unused, double *out_31529648679211919) {
   out_31529648679211919[0] = 0;
   out_31529648679211919[1] = 0;
   out_31529648679211919[2] = 0;
   out_31529648679211919[3] = 1;
   out_31529648679211919[4] = 0;
   out_31529648679211919[5] = 0;
   out_31529648679211919[6] = 0;
   out_31529648679211919[7] = 0;
   out_31529648679211919[8] = 0;
   out_31529648679211919[9] = 0;
   out_31529648679211919[10] = 0;
   out_31529648679211919[11] = 0;
   out_31529648679211919[12] = 0;
   out_31529648679211919[13] = 0;
   out_31529648679211919[14] = 0;
   out_31529648679211919[15] = 0;
   out_31529648679211919[16] = 0;
   out_31529648679211919[17] = 0;
   out_31529648679211919[18] = 0;
   out_31529648679211919[19] = 0;
   out_31529648679211919[20] = 0;
   out_31529648679211919[21] = 0;
   out_31529648679211919[22] = 1;
   out_31529648679211919[23] = 0;
   out_31529648679211919[24] = 0;
   out_31529648679211919[25] = 0;
   out_31529648679211919[26] = 0;
   out_31529648679211919[27] = 0;
   out_31529648679211919[28] = 0;
   out_31529648679211919[29] = 0;
   out_31529648679211919[30] = 0;
   out_31529648679211919[31] = 0;
   out_31529648679211919[32] = 0;
   out_31529648679211919[33] = 0;
   out_31529648679211919[34] = 0;
   out_31529648679211919[35] = 0;
   out_31529648679211919[36] = 0;
   out_31529648679211919[37] = 0;
   out_31529648679211919[38] = 0;
   out_31529648679211919[39] = 0;
   out_31529648679211919[40] = 0;
   out_31529648679211919[41] = 1;
   out_31529648679211919[42] = 0;
   out_31529648679211919[43] = 0;
   out_31529648679211919[44] = 0;
   out_31529648679211919[45] = 0;
   out_31529648679211919[46] = 0;
   out_31529648679211919[47] = 0;
   out_31529648679211919[48] = 0;
   out_31529648679211919[49] = 0;
   out_31529648679211919[50] = 0;
   out_31529648679211919[51] = 0;
   out_31529648679211919[52] = 0;
   out_31529648679211919[53] = 0;
}
void h_14(double *state, double *unused, double *out_1831988150759010376) {
   out_1831988150759010376[0] = state[6];
   out_1831988150759010376[1] = state[7];
   out_1831988150759010376[2] = state[8];
}
void H_14(double *state, double *unused, double *out_719437382327939809) {
   out_719437382327939809[0] = 0;
   out_719437382327939809[1] = 0;
   out_719437382327939809[2] = 0;
   out_719437382327939809[3] = 0;
   out_719437382327939809[4] = 0;
   out_719437382327939809[5] = 0;
   out_719437382327939809[6] = 1;
   out_719437382327939809[7] = 0;
   out_719437382327939809[8] = 0;
   out_719437382327939809[9] = 0;
   out_719437382327939809[10] = 0;
   out_719437382327939809[11] = 0;
   out_719437382327939809[12] = 0;
   out_719437382327939809[13] = 0;
   out_719437382327939809[14] = 0;
   out_719437382327939809[15] = 0;
   out_719437382327939809[16] = 0;
   out_719437382327939809[17] = 0;
   out_719437382327939809[18] = 0;
   out_719437382327939809[19] = 0;
   out_719437382327939809[20] = 0;
   out_719437382327939809[21] = 0;
   out_719437382327939809[22] = 0;
   out_719437382327939809[23] = 0;
   out_719437382327939809[24] = 0;
   out_719437382327939809[25] = 1;
   out_719437382327939809[26] = 0;
   out_719437382327939809[27] = 0;
   out_719437382327939809[28] = 0;
   out_719437382327939809[29] = 0;
   out_719437382327939809[30] = 0;
   out_719437382327939809[31] = 0;
   out_719437382327939809[32] = 0;
   out_719437382327939809[33] = 0;
   out_719437382327939809[34] = 0;
   out_719437382327939809[35] = 0;
   out_719437382327939809[36] = 0;
   out_719437382327939809[37] = 0;
   out_719437382327939809[38] = 0;
   out_719437382327939809[39] = 0;
   out_719437382327939809[40] = 0;
   out_719437382327939809[41] = 0;
   out_719437382327939809[42] = 0;
   out_719437382327939809[43] = 0;
   out_719437382327939809[44] = 1;
   out_719437382327939809[45] = 0;
   out_719437382327939809[46] = 0;
   out_719437382327939809[47] = 0;
   out_719437382327939809[48] = 0;
   out_719437382327939809[49] = 0;
   out_719437382327939809[50] = 0;
   out_719437382327939809[51] = 0;
   out_719437382327939809[52] = 0;
   out_719437382327939809[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_6914886810623359485) {
  err_fun(nom_x, delta_x, out_6914886810623359485);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1955170315450325036) {
  inv_err_fun(nom_x, true_x, out_1955170315450325036);
}
void pose_H_mod_fun(double *state, double *out_6464744367615017758) {
  H_mod_fun(state, out_6464744367615017758);
}
void pose_f_fun(double *state, double dt, double *out_843490903718422953) {
  f_fun(state,  dt, out_843490903718422953);
}
void pose_F_fun(double *state, double dt, double *out_8919071219298160156) {
  F_fun(state,  dt, out_8919071219298160156);
}
void pose_h_4(double *state, double *unused, double *out_173130356706362345) {
  h_4(state, unused, out_173130356706362345);
}
void pose_H_4(double *state, double *unused, double *out_3243803474011544720) {
  H_4(state, unused, out_3243803474011544720);
}
void pose_h_10(double *state, double *unused, double *out_3220967759669022070) {
  h_10(state, unused, out_3220967759669022070);
}
void pose_H_10(double *state, double *unused, double *out_7792322668041282962) {
  H_10(state, unused, out_7792322668041282962);
}
void pose_h_13(double *state, double *unused, double *out_5680375753611876010) {
  h_13(state, unused, out_5680375753611876010);
}
void pose_H_13(double *state, double *unused, double *out_31529648679211919) {
  H_13(state, unused, out_31529648679211919);
}
void pose_h_14(double *state, double *unused, double *out_1831988150759010376) {
  h_14(state, unused, out_1831988150759010376);
}
void pose_H_14(double *state, double *unused, double *out_719437382327939809) {
  H_14(state, unused, out_719437382327939809);
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
