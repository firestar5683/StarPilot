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
void err_fun(double *nom_x, double *delta_x, double *out_5867685499485526905) {
   out_5867685499485526905[0] = delta_x[0] + nom_x[0];
   out_5867685499485526905[1] = delta_x[1] + nom_x[1];
   out_5867685499485526905[2] = delta_x[2] + nom_x[2];
   out_5867685499485526905[3] = delta_x[3] + nom_x[3];
   out_5867685499485526905[4] = delta_x[4] + nom_x[4];
   out_5867685499485526905[5] = delta_x[5] + nom_x[5];
   out_5867685499485526905[6] = delta_x[6] + nom_x[6];
   out_5867685499485526905[7] = delta_x[7] + nom_x[7];
   out_5867685499485526905[8] = delta_x[8] + nom_x[8];
   out_5867685499485526905[9] = delta_x[9] + nom_x[9];
   out_5867685499485526905[10] = delta_x[10] + nom_x[10];
   out_5867685499485526905[11] = delta_x[11] + nom_x[11];
   out_5867685499485526905[12] = delta_x[12] + nom_x[12];
   out_5867685499485526905[13] = delta_x[13] + nom_x[13];
   out_5867685499485526905[14] = delta_x[14] + nom_x[14];
   out_5867685499485526905[15] = delta_x[15] + nom_x[15];
   out_5867685499485526905[16] = delta_x[16] + nom_x[16];
   out_5867685499485526905[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7496427572072330735) {
   out_7496427572072330735[0] = -nom_x[0] + true_x[0];
   out_7496427572072330735[1] = -nom_x[1] + true_x[1];
   out_7496427572072330735[2] = -nom_x[2] + true_x[2];
   out_7496427572072330735[3] = -nom_x[3] + true_x[3];
   out_7496427572072330735[4] = -nom_x[4] + true_x[4];
   out_7496427572072330735[5] = -nom_x[5] + true_x[5];
   out_7496427572072330735[6] = -nom_x[6] + true_x[6];
   out_7496427572072330735[7] = -nom_x[7] + true_x[7];
   out_7496427572072330735[8] = -nom_x[8] + true_x[8];
   out_7496427572072330735[9] = -nom_x[9] + true_x[9];
   out_7496427572072330735[10] = -nom_x[10] + true_x[10];
   out_7496427572072330735[11] = -nom_x[11] + true_x[11];
   out_7496427572072330735[12] = -nom_x[12] + true_x[12];
   out_7496427572072330735[13] = -nom_x[13] + true_x[13];
   out_7496427572072330735[14] = -nom_x[14] + true_x[14];
   out_7496427572072330735[15] = -nom_x[15] + true_x[15];
   out_7496427572072330735[16] = -nom_x[16] + true_x[16];
   out_7496427572072330735[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4599731282943687674) {
   out_4599731282943687674[0] = 1.0;
   out_4599731282943687674[1] = 0.0;
   out_4599731282943687674[2] = 0.0;
   out_4599731282943687674[3] = 0.0;
   out_4599731282943687674[4] = 0.0;
   out_4599731282943687674[5] = 0.0;
   out_4599731282943687674[6] = 0.0;
   out_4599731282943687674[7] = 0.0;
   out_4599731282943687674[8] = 0.0;
   out_4599731282943687674[9] = 0.0;
   out_4599731282943687674[10] = 0.0;
   out_4599731282943687674[11] = 0.0;
   out_4599731282943687674[12] = 0.0;
   out_4599731282943687674[13] = 0.0;
   out_4599731282943687674[14] = 0.0;
   out_4599731282943687674[15] = 0.0;
   out_4599731282943687674[16] = 0.0;
   out_4599731282943687674[17] = 0.0;
   out_4599731282943687674[18] = 0.0;
   out_4599731282943687674[19] = 1.0;
   out_4599731282943687674[20] = 0.0;
   out_4599731282943687674[21] = 0.0;
   out_4599731282943687674[22] = 0.0;
   out_4599731282943687674[23] = 0.0;
   out_4599731282943687674[24] = 0.0;
   out_4599731282943687674[25] = 0.0;
   out_4599731282943687674[26] = 0.0;
   out_4599731282943687674[27] = 0.0;
   out_4599731282943687674[28] = 0.0;
   out_4599731282943687674[29] = 0.0;
   out_4599731282943687674[30] = 0.0;
   out_4599731282943687674[31] = 0.0;
   out_4599731282943687674[32] = 0.0;
   out_4599731282943687674[33] = 0.0;
   out_4599731282943687674[34] = 0.0;
   out_4599731282943687674[35] = 0.0;
   out_4599731282943687674[36] = 0.0;
   out_4599731282943687674[37] = 0.0;
   out_4599731282943687674[38] = 1.0;
   out_4599731282943687674[39] = 0.0;
   out_4599731282943687674[40] = 0.0;
   out_4599731282943687674[41] = 0.0;
   out_4599731282943687674[42] = 0.0;
   out_4599731282943687674[43] = 0.0;
   out_4599731282943687674[44] = 0.0;
   out_4599731282943687674[45] = 0.0;
   out_4599731282943687674[46] = 0.0;
   out_4599731282943687674[47] = 0.0;
   out_4599731282943687674[48] = 0.0;
   out_4599731282943687674[49] = 0.0;
   out_4599731282943687674[50] = 0.0;
   out_4599731282943687674[51] = 0.0;
   out_4599731282943687674[52] = 0.0;
   out_4599731282943687674[53] = 0.0;
   out_4599731282943687674[54] = 0.0;
   out_4599731282943687674[55] = 0.0;
   out_4599731282943687674[56] = 0.0;
   out_4599731282943687674[57] = 1.0;
   out_4599731282943687674[58] = 0.0;
   out_4599731282943687674[59] = 0.0;
   out_4599731282943687674[60] = 0.0;
   out_4599731282943687674[61] = 0.0;
   out_4599731282943687674[62] = 0.0;
   out_4599731282943687674[63] = 0.0;
   out_4599731282943687674[64] = 0.0;
   out_4599731282943687674[65] = 0.0;
   out_4599731282943687674[66] = 0.0;
   out_4599731282943687674[67] = 0.0;
   out_4599731282943687674[68] = 0.0;
   out_4599731282943687674[69] = 0.0;
   out_4599731282943687674[70] = 0.0;
   out_4599731282943687674[71] = 0.0;
   out_4599731282943687674[72] = 0.0;
   out_4599731282943687674[73] = 0.0;
   out_4599731282943687674[74] = 0.0;
   out_4599731282943687674[75] = 0.0;
   out_4599731282943687674[76] = 1.0;
   out_4599731282943687674[77] = 0.0;
   out_4599731282943687674[78] = 0.0;
   out_4599731282943687674[79] = 0.0;
   out_4599731282943687674[80] = 0.0;
   out_4599731282943687674[81] = 0.0;
   out_4599731282943687674[82] = 0.0;
   out_4599731282943687674[83] = 0.0;
   out_4599731282943687674[84] = 0.0;
   out_4599731282943687674[85] = 0.0;
   out_4599731282943687674[86] = 0.0;
   out_4599731282943687674[87] = 0.0;
   out_4599731282943687674[88] = 0.0;
   out_4599731282943687674[89] = 0.0;
   out_4599731282943687674[90] = 0.0;
   out_4599731282943687674[91] = 0.0;
   out_4599731282943687674[92] = 0.0;
   out_4599731282943687674[93] = 0.0;
   out_4599731282943687674[94] = 0.0;
   out_4599731282943687674[95] = 1.0;
   out_4599731282943687674[96] = 0.0;
   out_4599731282943687674[97] = 0.0;
   out_4599731282943687674[98] = 0.0;
   out_4599731282943687674[99] = 0.0;
   out_4599731282943687674[100] = 0.0;
   out_4599731282943687674[101] = 0.0;
   out_4599731282943687674[102] = 0.0;
   out_4599731282943687674[103] = 0.0;
   out_4599731282943687674[104] = 0.0;
   out_4599731282943687674[105] = 0.0;
   out_4599731282943687674[106] = 0.0;
   out_4599731282943687674[107] = 0.0;
   out_4599731282943687674[108] = 0.0;
   out_4599731282943687674[109] = 0.0;
   out_4599731282943687674[110] = 0.0;
   out_4599731282943687674[111] = 0.0;
   out_4599731282943687674[112] = 0.0;
   out_4599731282943687674[113] = 0.0;
   out_4599731282943687674[114] = 1.0;
   out_4599731282943687674[115] = 0.0;
   out_4599731282943687674[116] = 0.0;
   out_4599731282943687674[117] = 0.0;
   out_4599731282943687674[118] = 0.0;
   out_4599731282943687674[119] = 0.0;
   out_4599731282943687674[120] = 0.0;
   out_4599731282943687674[121] = 0.0;
   out_4599731282943687674[122] = 0.0;
   out_4599731282943687674[123] = 0.0;
   out_4599731282943687674[124] = 0.0;
   out_4599731282943687674[125] = 0.0;
   out_4599731282943687674[126] = 0.0;
   out_4599731282943687674[127] = 0.0;
   out_4599731282943687674[128] = 0.0;
   out_4599731282943687674[129] = 0.0;
   out_4599731282943687674[130] = 0.0;
   out_4599731282943687674[131] = 0.0;
   out_4599731282943687674[132] = 0.0;
   out_4599731282943687674[133] = 1.0;
   out_4599731282943687674[134] = 0.0;
   out_4599731282943687674[135] = 0.0;
   out_4599731282943687674[136] = 0.0;
   out_4599731282943687674[137] = 0.0;
   out_4599731282943687674[138] = 0.0;
   out_4599731282943687674[139] = 0.0;
   out_4599731282943687674[140] = 0.0;
   out_4599731282943687674[141] = 0.0;
   out_4599731282943687674[142] = 0.0;
   out_4599731282943687674[143] = 0.0;
   out_4599731282943687674[144] = 0.0;
   out_4599731282943687674[145] = 0.0;
   out_4599731282943687674[146] = 0.0;
   out_4599731282943687674[147] = 0.0;
   out_4599731282943687674[148] = 0.0;
   out_4599731282943687674[149] = 0.0;
   out_4599731282943687674[150] = 0.0;
   out_4599731282943687674[151] = 0.0;
   out_4599731282943687674[152] = 1.0;
   out_4599731282943687674[153] = 0.0;
   out_4599731282943687674[154] = 0.0;
   out_4599731282943687674[155] = 0.0;
   out_4599731282943687674[156] = 0.0;
   out_4599731282943687674[157] = 0.0;
   out_4599731282943687674[158] = 0.0;
   out_4599731282943687674[159] = 0.0;
   out_4599731282943687674[160] = 0.0;
   out_4599731282943687674[161] = 0.0;
   out_4599731282943687674[162] = 0.0;
   out_4599731282943687674[163] = 0.0;
   out_4599731282943687674[164] = 0.0;
   out_4599731282943687674[165] = 0.0;
   out_4599731282943687674[166] = 0.0;
   out_4599731282943687674[167] = 0.0;
   out_4599731282943687674[168] = 0.0;
   out_4599731282943687674[169] = 0.0;
   out_4599731282943687674[170] = 0.0;
   out_4599731282943687674[171] = 1.0;
   out_4599731282943687674[172] = 0.0;
   out_4599731282943687674[173] = 0.0;
   out_4599731282943687674[174] = 0.0;
   out_4599731282943687674[175] = 0.0;
   out_4599731282943687674[176] = 0.0;
   out_4599731282943687674[177] = 0.0;
   out_4599731282943687674[178] = 0.0;
   out_4599731282943687674[179] = 0.0;
   out_4599731282943687674[180] = 0.0;
   out_4599731282943687674[181] = 0.0;
   out_4599731282943687674[182] = 0.0;
   out_4599731282943687674[183] = 0.0;
   out_4599731282943687674[184] = 0.0;
   out_4599731282943687674[185] = 0.0;
   out_4599731282943687674[186] = 0.0;
   out_4599731282943687674[187] = 0.0;
   out_4599731282943687674[188] = 0.0;
   out_4599731282943687674[189] = 0.0;
   out_4599731282943687674[190] = 1.0;
   out_4599731282943687674[191] = 0.0;
   out_4599731282943687674[192] = 0.0;
   out_4599731282943687674[193] = 0.0;
   out_4599731282943687674[194] = 0.0;
   out_4599731282943687674[195] = 0.0;
   out_4599731282943687674[196] = 0.0;
   out_4599731282943687674[197] = 0.0;
   out_4599731282943687674[198] = 0.0;
   out_4599731282943687674[199] = 0.0;
   out_4599731282943687674[200] = 0.0;
   out_4599731282943687674[201] = 0.0;
   out_4599731282943687674[202] = 0.0;
   out_4599731282943687674[203] = 0.0;
   out_4599731282943687674[204] = 0.0;
   out_4599731282943687674[205] = 0.0;
   out_4599731282943687674[206] = 0.0;
   out_4599731282943687674[207] = 0.0;
   out_4599731282943687674[208] = 0.0;
   out_4599731282943687674[209] = 1.0;
   out_4599731282943687674[210] = 0.0;
   out_4599731282943687674[211] = 0.0;
   out_4599731282943687674[212] = 0.0;
   out_4599731282943687674[213] = 0.0;
   out_4599731282943687674[214] = 0.0;
   out_4599731282943687674[215] = 0.0;
   out_4599731282943687674[216] = 0.0;
   out_4599731282943687674[217] = 0.0;
   out_4599731282943687674[218] = 0.0;
   out_4599731282943687674[219] = 0.0;
   out_4599731282943687674[220] = 0.0;
   out_4599731282943687674[221] = 0.0;
   out_4599731282943687674[222] = 0.0;
   out_4599731282943687674[223] = 0.0;
   out_4599731282943687674[224] = 0.0;
   out_4599731282943687674[225] = 0.0;
   out_4599731282943687674[226] = 0.0;
   out_4599731282943687674[227] = 0.0;
   out_4599731282943687674[228] = 1.0;
   out_4599731282943687674[229] = 0.0;
   out_4599731282943687674[230] = 0.0;
   out_4599731282943687674[231] = 0.0;
   out_4599731282943687674[232] = 0.0;
   out_4599731282943687674[233] = 0.0;
   out_4599731282943687674[234] = 0.0;
   out_4599731282943687674[235] = 0.0;
   out_4599731282943687674[236] = 0.0;
   out_4599731282943687674[237] = 0.0;
   out_4599731282943687674[238] = 0.0;
   out_4599731282943687674[239] = 0.0;
   out_4599731282943687674[240] = 0.0;
   out_4599731282943687674[241] = 0.0;
   out_4599731282943687674[242] = 0.0;
   out_4599731282943687674[243] = 0.0;
   out_4599731282943687674[244] = 0.0;
   out_4599731282943687674[245] = 0.0;
   out_4599731282943687674[246] = 0.0;
   out_4599731282943687674[247] = 1.0;
   out_4599731282943687674[248] = 0.0;
   out_4599731282943687674[249] = 0.0;
   out_4599731282943687674[250] = 0.0;
   out_4599731282943687674[251] = 0.0;
   out_4599731282943687674[252] = 0.0;
   out_4599731282943687674[253] = 0.0;
   out_4599731282943687674[254] = 0.0;
   out_4599731282943687674[255] = 0.0;
   out_4599731282943687674[256] = 0.0;
   out_4599731282943687674[257] = 0.0;
   out_4599731282943687674[258] = 0.0;
   out_4599731282943687674[259] = 0.0;
   out_4599731282943687674[260] = 0.0;
   out_4599731282943687674[261] = 0.0;
   out_4599731282943687674[262] = 0.0;
   out_4599731282943687674[263] = 0.0;
   out_4599731282943687674[264] = 0.0;
   out_4599731282943687674[265] = 0.0;
   out_4599731282943687674[266] = 1.0;
   out_4599731282943687674[267] = 0.0;
   out_4599731282943687674[268] = 0.0;
   out_4599731282943687674[269] = 0.0;
   out_4599731282943687674[270] = 0.0;
   out_4599731282943687674[271] = 0.0;
   out_4599731282943687674[272] = 0.0;
   out_4599731282943687674[273] = 0.0;
   out_4599731282943687674[274] = 0.0;
   out_4599731282943687674[275] = 0.0;
   out_4599731282943687674[276] = 0.0;
   out_4599731282943687674[277] = 0.0;
   out_4599731282943687674[278] = 0.0;
   out_4599731282943687674[279] = 0.0;
   out_4599731282943687674[280] = 0.0;
   out_4599731282943687674[281] = 0.0;
   out_4599731282943687674[282] = 0.0;
   out_4599731282943687674[283] = 0.0;
   out_4599731282943687674[284] = 0.0;
   out_4599731282943687674[285] = 1.0;
   out_4599731282943687674[286] = 0.0;
   out_4599731282943687674[287] = 0.0;
   out_4599731282943687674[288] = 0.0;
   out_4599731282943687674[289] = 0.0;
   out_4599731282943687674[290] = 0.0;
   out_4599731282943687674[291] = 0.0;
   out_4599731282943687674[292] = 0.0;
   out_4599731282943687674[293] = 0.0;
   out_4599731282943687674[294] = 0.0;
   out_4599731282943687674[295] = 0.0;
   out_4599731282943687674[296] = 0.0;
   out_4599731282943687674[297] = 0.0;
   out_4599731282943687674[298] = 0.0;
   out_4599731282943687674[299] = 0.0;
   out_4599731282943687674[300] = 0.0;
   out_4599731282943687674[301] = 0.0;
   out_4599731282943687674[302] = 0.0;
   out_4599731282943687674[303] = 0.0;
   out_4599731282943687674[304] = 1.0;
   out_4599731282943687674[305] = 0.0;
   out_4599731282943687674[306] = 0.0;
   out_4599731282943687674[307] = 0.0;
   out_4599731282943687674[308] = 0.0;
   out_4599731282943687674[309] = 0.0;
   out_4599731282943687674[310] = 0.0;
   out_4599731282943687674[311] = 0.0;
   out_4599731282943687674[312] = 0.0;
   out_4599731282943687674[313] = 0.0;
   out_4599731282943687674[314] = 0.0;
   out_4599731282943687674[315] = 0.0;
   out_4599731282943687674[316] = 0.0;
   out_4599731282943687674[317] = 0.0;
   out_4599731282943687674[318] = 0.0;
   out_4599731282943687674[319] = 0.0;
   out_4599731282943687674[320] = 0.0;
   out_4599731282943687674[321] = 0.0;
   out_4599731282943687674[322] = 0.0;
   out_4599731282943687674[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8448766243959956852) {
   out_8448766243959956852[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8448766243959956852[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8448766243959956852[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8448766243959956852[3] = dt*state[12] + state[3];
   out_8448766243959956852[4] = dt*state[13] + state[4];
   out_8448766243959956852[5] = dt*state[14] + state[5];
   out_8448766243959956852[6] = state[6];
   out_8448766243959956852[7] = state[7];
   out_8448766243959956852[8] = state[8];
   out_8448766243959956852[9] = state[9];
   out_8448766243959956852[10] = state[10];
   out_8448766243959956852[11] = state[11];
   out_8448766243959956852[12] = state[12];
   out_8448766243959956852[13] = state[13];
   out_8448766243959956852[14] = state[14];
   out_8448766243959956852[15] = state[15];
   out_8448766243959956852[16] = state[16];
   out_8448766243959956852[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3524034210859456461) {
   out_3524034210859456461[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3524034210859456461[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3524034210859456461[2] = 0;
   out_3524034210859456461[3] = 0;
   out_3524034210859456461[4] = 0;
   out_3524034210859456461[5] = 0;
   out_3524034210859456461[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3524034210859456461[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3524034210859456461[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3524034210859456461[9] = 0;
   out_3524034210859456461[10] = 0;
   out_3524034210859456461[11] = 0;
   out_3524034210859456461[12] = 0;
   out_3524034210859456461[13] = 0;
   out_3524034210859456461[14] = 0;
   out_3524034210859456461[15] = 0;
   out_3524034210859456461[16] = 0;
   out_3524034210859456461[17] = 0;
   out_3524034210859456461[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3524034210859456461[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3524034210859456461[20] = 0;
   out_3524034210859456461[21] = 0;
   out_3524034210859456461[22] = 0;
   out_3524034210859456461[23] = 0;
   out_3524034210859456461[24] = 0;
   out_3524034210859456461[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3524034210859456461[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3524034210859456461[27] = 0;
   out_3524034210859456461[28] = 0;
   out_3524034210859456461[29] = 0;
   out_3524034210859456461[30] = 0;
   out_3524034210859456461[31] = 0;
   out_3524034210859456461[32] = 0;
   out_3524034210859456461[33] = 0;
   out_3524034210859456461[34] = 0;
   out_3524034210859456461[35] = 0;
   out_3524034210859456461[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3524034210859456461[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3524034210859456461[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3524034210859456461[39] = 0;
   out_3524034210859456461[40] = 0;
   out_3524034210859456461[41] = 0;
   out_3524034210859456461[42] = 0;
   out_3524034210859456461[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3524034210859456461[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3524034210859456461[45] = 0;
   out_3524034210859456461[46] = 0;
   out_3524034210859456461[47] = 0;
   out_3524034210859456461[48] = 0;
   out_3524034210859456461[49] = 0;
   out_3524034210859456461[50] = 0;
   out_3524034210859456461[51] = 0;
   out_3524034210859456461[52] = 0;
   out_3524034210859456461[53] = 0;
   out_3524034210859456461[54] = 0;
   out_3524034210859456461[55] = 0;
   out_3524034210859456461[56] = 0;
   out_3524034210859456461[57] = 1;
   out_3524034210859456461[58] = 0;
   out_3524034210859456461[59] = 0;
   out_3524034210859456461[60] = 0;
   out_3524034210859456461[61] = 0;
   out_3524034210859456461[62] = 0;
   out_3524034210859456461[63] = 0;
   out_3524034210859456461[64] = 0;
   out_3524034210859456461[65] = 0;
   out_3524034210859456461[66] = dt;
   out_3524034210859456461[67] = 0;
   out_3524034210859456461[68] = 0;
   out_3524034210859456461[69] = 0;
   out_3524034210859456461[70] = 0;
   out_3524034210859456461[71] = 0;
   out_3524034210859456461[72] = 0;
   out_3524034210859456461[73] = 0;
   out_3524034210859456461[74] = 0;
   out_3524034210859456461[75] = 0;
   out_3524034210859456461[76] = 1;
   out_3524034210859456461[77] = 0;
   out_3524034210859456461[78] = 0;
   out_3524034210859456461[79] = 0;
   out_3524034210859456461[80] = 0;
   out_3524034210859456461[81] = 0;
   out_3524034210859456461[82] = 0;
   out_3524034210859456461[83] = 0;
   out_3524034210859456461[84] = 0;
   out_3524034210859456461[85] = dt;
   out_3524034210859456461[86] = 0;
   out_3524034210859456461[87] = 0;
   out_3524034210859456461[88] = 0;
   out_3524034210859456461[89] = 0;
   out_3524034210859456461[90] = 0;
   out_3524034210859456461[91] = 0;
   out_3524034210859456461[92] = 0;
   out_3524034210859456461[93] = 0;
   out_3524034210859456461[94] = 0;
   out_3524034210859456461[95] = 1;
   out_3524034210859456461[96] = 0;
   out_3524034210859456461[97] = 0;
   out_3524034210859456461[98] = 0;
   out_3524034210859456461[99] = 0;
   out_3524034210859456461[100] = 0;
   out_3524034210859456461[101] = 0;
   out_3524034210859456461[102] = 0;
   out_3524034210859456461[103] = 0;
   out_3524034210859456461[104] = dt;
   out_3524034210859456461[105] = 0;
   out_3524034210859456461[106] = 0;
   out_3524034210859456461[107] = 0;
   out_3524034210859456461[108] = 0;
   out_3524034210859456461[109] = 0;
   out_3524034210859456461[110] = 0;
   out_3524034210859456461[111] = 0;
   out_3524034210859456461[112] = 0;
   out_3524034210859456461[113] = 0;
   out_3524034210859456461[114] = 1;
   out_3524034210859456461[115] = 0;
   out_3524034210859456461[116] = 0;
   out_3524034210859456461[117] = 0;
   out_3524034210859456461[118] = 0;
   out_3524034210859456461[119] = 0;
   out_3524034210859456461[120] = 0;
   out_3524034210859456461[121] = 0;
   out_3524034210859456461[122] = 0;
   out_3524034210859456461[123] = 0;
   out_3524034210859456461[124] = 0;
   out_3524034210859456461[125] = 0;
   out_3524034210859456461[126] = 0;
   out_3524034210859456461[127] = 0;
   out_3524034210859456461[128] = 0;
   out_3524034210859456461[129] = 0;
   out_3524034210859456461[130] = 0;
   out_3524034210859456461[131] = 0;
   out_3524034210859456461[132] = 0;
   out_3524034210859456461[133] = 1;
   out_3524034210859456461[134] = 0;
   out_3524034210859456461[135] = 0;
   out_3524034210859456461[136] = 0;
   out_3524034210859456461[137] = 0;
   out_3524034210859456461[138] = 0;
   out_3524034210859456461[139] = 0;
   out_3524034210859456461[140] = 0;
   out_3524034210859456461[141] = 0;
   out_3524034210859456461[142] = 0;
   out_3524034210859456461[143] = 0;
   out_3524034210859456461[144] = 0;
   out_3524034210859456461[145] = 0;
   out_3524034210859456461[146] = 0;
   out_3524034210859456461[147] = 0;
   out_3524034210859456461[148] = 0;
   out_3524034210859456461[149] = 0;
   out_3524034210859456461[150] = 0;
   out_3524034210859456461[151] = 0;
   out_3524034210859456461[152] = 1;
   out_3524034210859456461[153] = 0;
   out_3524034210859456461[154] = 0;
   out_3524034210859456461[155] = 0;
   out_3524034210859456461[156] = 0;
   out_3524034210859456461[157] = 0;
   out_3524034210859456461[158] = 0;
   out_3524034210859456461[159] = 0;
   out_3524034210859456461[160] = 0;
   out_3524034210859456461[161] = 0;
   out_3524034210859456461[162] = 0;
   out_3524034210859456461[163] = 0;
   out_3524034210859456461[164] = 0;
   out_3524034210859456461[165] = 0;
   out_3524034210859456461[166] = 0;
   out_3524034210859456461[167] = 0;
   out_3524034210859456461[168] = 0;
   out_3524034210859456461[169] = 0;
   out_3524034210859456461[170] = 0;
   out_3524034210859456461[171] = 1;
   out_3524034210859456461[172] = 0;
   out_3524034210859456461[173] = 0;
   out_3524034210859456461[174] = 0;
   out_3524034210859456461[175] = 0;
   out_3524034210859456461[176] = 0;
   out_3524034210859456461[177] = 0;
   out_3524034210859456461[178] = 0;
   out_3524034210859456461[179] = 0;
   out_3524034210859456461[180] = 0;
   out_3524034210859456461[181] = 0;
   out_3524034210859456461[182] = 0;
   out_3524034210859456461[183] = 0;
   out_3524034210859456461[184] = 0;
   out_3524034210859456461[185] = 0;
   out_3524034210859456461[186] = 0;
   out_3524034210859456461[187] = 0;
   out_3524034210859456461[188] = 0;
   out_3524034210859456461[189] = 0;
   out_3524034210859456461[190] = 1;
   out_3524034210859456461[191] = 0;
   out_3524034210859456461[192] = 0;
   out_3524034210859456461[193] = 0;
   out_3524034210859456461[194] = 0;
   out_3524034210859456461[195] = 0;
   out_3524034210859456461[196] = 0;
   out_3524034210859456461[197] = 0;
   out_3524034210859456461[198] = 0;
   out_3524034210859456461[199] = 0;
   out_3524034210859456461[200] = 0;
   out_3524034210859456461[201] = 0;
   out_3524034210859456461[202] = 0;
   out_3524034210859456461[203] = 0;
   out_3524034210859456461[204] = 0;
   out_3524034210859456461[205] = 0;
   out_3524034210859456461[206] = 0;
   out_3524034210859456461[207] = 0;
   out_3524034210859456461[208] = 0;
   out_3524034210859456461[209] = 1;
   out_3524034210859456461[210] = 0;
   out_3524034210859456461[211] = 0;
   out_3524034210859456461[212] = 0;
   out_3524034210859456461[213] = 0;
   out_3524034210859456461[214] = 0;
   out_3524034210859456461[215] = 0;
   out_3524034210859456461[216] = 0;
   out_3524034210859456461[217] = 0;
   out_3524034210859456461[218] = 0;
   out_3524034210859456461[219] = 0;
   out_3524034210859456461[220] = 0;
   out_3524034210859456461[221] = 0;
   out_3524034210859456461[222] = 0;
   out_3524034210859456461[223] = 0;
   out_3524034210859456461[224] = 0;
   out_3524034210859456461[225] = 0;
   out_3524034210859456461[226] = 0;
   out_3524034210859456461[227] = 0;
   out_3524034210859456461[228] = 1;
   out_3524034210859456461[229] = 0;
   out_3524034210859456461[230] = 0;
   out_3524034210859456461[231] = 0;
   out_3524034210859456461[232] = 0;
   out_3524034210859456461[233] = 0;
   out_3524034210859456461[234] = 0;
   out_3524034210859456461[235] = 0;
   out_3524034210859456461[236] = 0;
   out_3524034210859456461[237] = 0;
   out_3524034210859456461[238] = 0;
   out_3524034210859456461[239] = 0;
   out_3524034210859456461[240] = 0;
   out_3524034210859456461[241] = 0;
   out_3524034210859456461[242] = 0;
   out_3524034210859456461[243] = 0;
   out_3524034210859456461[244] = 0;
   out_3524034210859456461[245] = 0;
   out_3524034210859456461[246] = 0;
   out_3524034210859456461[247] = 1;
   out_3524034210859456461[248] = 0;
   out_3524034210859456461[249] = 0;
   out_3524034210859456461[250] = 0;
   out_3524034210859456461[251] = 0;
   out_3524034210859456461[252] = 0;
   out_3524034210859456461[253] = 0;
   out_3524034210859456461[254] = 0;
   out_3524034210859456461[255] = 0;
   out_3524034210859456461[256] = 0;
   out_3524034210859456461[257] = 0;
   out_3524034210859456461[258] = 0;
   out_3524034210859456461[259] = 0;
   out_3524034210859456461[260] = 0;
   out_3524034210859456461[261] = 0;
   out_3524034210859456461[262] = 0;
   out_3524034210859456461[263] = 0;
   out_3524034210859456461[264] = 0;
   out_3524034210859456461[265] = 0;
   out_3524034210859456461[266] = 1;
   out_3524034210859456461[267] = 0;
   out_3524034210859456461[268] = 0;
   out_3524034210859456461[269] = 0;
   out_3524034210859456461[270] = 0;
   out_3524034210859456461[271] = 0;
   out_3524034210859456461[272] = 0;
   out_3524034210859456461[273] = 0;
   out_3524034210859456461[274] = 0;
   out_3524034210859456461[275] = 0;
   out_3524034210859456461[276] = 0;
   out_3524034210859456461[277] = 0;
   out_3524034210859456461[278] = 0;
   out_3524034210859456461[279] = 0;
   out_3524034210859456461[280] = 0;
   out_3524034210859456461[281] = 0;
   out_3524034210859456461[282] = 0;
   out_3524034210859456461[283] = 0;
   out_3524034210859456461[284] = 0;
   out_3524034210859456461[285] = 1;
   out_3524034210859456461[286] = 0;
   out_3524034210859456461[287] = 0;
   out_3524034210859456461[288] = 0;
   out_3524034210859456461[289] = 0;
   out_3524034210859456461[290] = 0;
   out_3524034210859456461[291] = 0;
   out_3524034210859456461[292] = 0;
   out_3524034210859456461[293] = 0;
   out_3524034210859456461[294] = 0;
   out_3524034210859456461[295] = 0;
   out_3524034210859456461[296] = 0;
   out_3524034210859456461[297] = 0;
   out_3524034210859456461[298] = 0;
   out_3524034210859456461[299] = 0;
   out_3524034210859456461[300] = 0;
   out_3524034210859456461[301] = 0;
   out_3524034210859456461[302] = 0;
   out_3524034210859456461[303] = 0;
   out_3524034210859456461[304] = 1;
   out_3524034210859456461[305] = 0;
   out_3524034210859456461[306] = 0;
   out_3524034210859456461[307] = 0;
   out_3524034210859456461[308] = 0;
   out_3524034210859456461[309] = 0;
   out_3524034210859456461[310] = 0;
   out_3524034210859456461[311] = 0;
   out_3524034210859456461[312] = 0;
   out_3524034210859456461[313] = 0;
   out_3524034210859456461[314] = 0;
   out_3524034210859456461[315] = 0;
   out_3524034210859456461[316] = 0;
   out_3524034210859456461[317] = 0;
   out_3524034210859456461[318] = 0;
   out_3524034210859456461[319] = 0;
   out_3524034210859456461[320] = 0;
   out_3524034210859456461[321] = 0;
   out_3524034210859456461[322] = 0;
   out_3524034210859456461[323] = 1;
}
void h_4(double *state, double *unused, double *out_1468084297579901706) {
   out_1468084297579901706[0] = state[6] + state[9];
   out_1468084297579901706[1] = state[7] + state[10];
   out_1468084297579901706[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_552787102095393061) {
   out_552787102095393061[0] = 0;
   out_552787102095393061[1] = 0;
   out_552787102095393061[2] = 0;
   out_552787102095393061[3] = 0;
   out_552787102095393061[4] = 0;
   out_552787102095393061[5] = 0;
   out_552787102095393061[6] = 1;
   out_552787102095393061[7] = 0;
   out_552787102095393061[8] = 0;
   out_552787102095393061[9] = 1;
   out_552787102095393061[10] = 0;
   out_552787102095393061[11] = 0;
   out_552787102095393061[12] = 0;
   out_552787102095393061[13] = 0;
   out_552787102095393061[14] = 0;
   out_552787102095393061[15] = 0;
   out_552787102095393061[16] = 0;
   out_552787102095393061[17] = 0;
   out_552787102095393061[18] = 0;
   out_552787102095393061[19] = 0;
   out_552787102095393061[20] = 0;
   out_552787102095393061[21] = 0;
   out_552787102095393061[22] = 0;
   out_552787102095393061[23] = 0;
   out_552787102095393061[24] = 0;
   out_552787102095393061[25] = 1;
   out_552787102095393061[26] = 0;
   out_552787102095393061[27] = 0;
   out_552787102095393061[28] = 1;
   out_552787102095393061[29] = 0;
   out_552787102095393061[30] = 0;
   out_552787102095393061[31] = 0;
   out_552787102095393061[32] = 0;
   out_552787102095393061[33] = 0;
   out_552787102095393061[34] = 0;
   out_552787102095393061[35] = 0;
   out_552787102095393061[36] = 0;
   out_552787102095393061[37] = 0;
   out_552787102095393061[38] = 0;
   out_552787102095393061[39] = 0;
   out_552787102095393061[40] = 0;
   out_552787102095393061[41] = 0;
   out_552787102095393061[42] = 0;
   out_552787102095393061[43] = 0;
   out_552787102095393061[44] = 1;
   out_552787102095393061[45] = 0;
   out_552787102095393061[46] = 0;
   out_552787102095393061[47] = 1;
   out_552787102095393061[48] = 0;
   out_552787102095393061[49] = 0;
   out_552787102095393061[50] = 0;
   out_552787102095393061[51] = 0;
   out_552787102095393061[52] = 0;
   out_552787102095393061[53] = 0;
}
void h_10(double *state, double *unused, double *out_1051779536617211070) {
   out_1051779536617211070[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1051779536617211070[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1051779536617211070[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7440841037325716699) {
   out_7440841037325716699[0] = 0;
   out_7440841037325716699[1] = 9.8100000000000005*cos(state[1]);
   out_7440841037325716699[2] = 0;
   out_7440841037325716699[3] = 0;
   out_7440841037325716699[4] = -state[8];
   out_7440841037325716699[5] = state[7];
   out_7440841037325716699[6] = 0;
   out_7440841037325716699[7] = state[5];
   out_7440841037325716699[8] = -state[4];
   out_7440841037325716699[9] = 0;
   out_7440841037325716699[10] = 0;
   out_7440841037325716699[11] = 0;
   out_7440841037325716699[12] = 1;
   out_7440841037325716699[13] = 0;
   out_7440841037325716699[14] = 0;
   out_7440841037325716699[15] = 1;
   out_7440841037325716699[16] = 0;
   out_7440841037325716699[17] = 0;
   out_7440841037325716699[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7440841037325716699[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7440841037325716699[20] = 0;
   out_7440841037325716699[21] = state[8];
   out_7440841037325716699[22] = 0;
   out_7440841037325716699[23] = -state[6];
   out_7440841037325716699[24] = -state[5];
   out_7440841037325716699[25] = 0;
   out_7440841037325716699[26] = state[3];
   out_7440841037325716699[27] = 0;
   out_7440841037325716699[28] = 0;
   out_7440841037325716699[29] = 0;
   out_7440841037325716699[30] = 0;
   out_7440841037325716699[31] = 1;
   out_7440841037325716699[32] = 0;
   out_7440841037325716699[33] = 0;
   out_7440841037325716699[34] = 1;
   out_7440841037325716699[35] = 0;
   out_7440841037325716699[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7440841037325716699[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7440841037325716699[38] = 0;
   out_7440841037325716699[39] = -state[7];
   out_7440841037325716699[40] = state[6];
   out_7440841037325716699[41] = 0;
   out_7440841037325716699[42] = state[4];
   out_7440841037325716699[43] = -state[3];
   out_7440841037325716699[44] = 0;
   out_7440841037325716699[45] = 0;
   out_7440841037325716699[46] = 0;
   out_7440841037325716699[47] = 0;
   out_7440841037325716699[48] = 0;
   out_7440841037325716699[49] = 0;
   out_7440841037325716699[50] = 1;
   out_7440841037325716699[51] = 0;
   out_7440841037325716699[52] = 0;
   out_7440841037325716699[53] = 1;
}
void h_13(double *state, double *unused, double *out_4266757043601180240) {
   out_4266757043601180240[0] = state[3];
   out_4266757043601180240[1] = state[4];
   out_4266757043601180240[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3765060927427725862) {
   out_3765060927427725862[0] = 0;
   out_3765060927427725862[1] = 0;
   out_3765060927427725862[2] = 0;
   out_3765060927427725862[3] = 1;
   out_3765060927427725862[4] = 0;
   out_3765060927427725862[5] = 0;
   out_3765060927427725862[6] = 0;
   out_3765060927427725862[7] = 0;
   out_3765060927427725862[8] = 0;
   out_3765060927427725862[9] = 0;
   out_3765060927427725862[10] = 0;
   out_3765060927427725862[11] = 0;
   out_3765060927427725862[12] = 0;
   out_3765060927427725862[13] = 0;
   out_3765060927427725862[14] = 0;
   out_3765060927427725862[15] = 0;
   out_3765060927427725862[16] = 0;
   out_3765060927427725862[17] = 0;
   out_3765060927427725862[18] = 0;
   out_3765060927427725862[19] = 0;
   out_3765060927427725862[20] = 0;
   out_3765060927427725862[21] = 0;
   out_3765060927427725862[22] = 1;
   out_3765060927427725862[23] = 0;
   out_3765060927427725862[24] = 0;
   out_3765060927427725862[25] = 0;
   out_3765060927427725862[26] = 0;
   out_3765060927427725862[27] = 0;
   out_3765060927427725862[28] = 0;
   out_3765060927427725862[29] = 0;
   out_3765060927427725862[30] = 0;
   out_3765060927427725862[31] = 0;
   out_3765060927427725862[32] = 0;
   out_3765060927427725862[33] = 0;
   out_3765060927427725862[34] = 0;
   out_3765060927427725862[35] = 0;
   out_3765060927427725862[36] = 0;
   out_3765060927427725862[37] = 0;
   out_3765060927427725862[38] = 0;
   out_3765060927427725862[39] = 0;
   out_3765060927427725862[40] = 0;
   out_3765060927427725862[41] = 1;
   out_3765060927427725862[42] = 0;
   out_3765060927427725862[43] = 0;
   out_3765060927427725862[44] = 0;
   out_3765060927427725862[45] = 0;
   out_3765060927427725862[46] = 0;
   out_3765060927427725862[47] = 0;
   out_3765060927427725862[48] = 0;
   out_3765060927427725862[49] = 0;
   out_3765060927427725862[50] = 0;
   out_3765060927427725862[51] = 0;
   out_3765060927427725862[52] = 0;
   out_3765060927427725862[53] = 0;
}
void h_14(double *state, double *unused, double *out_1847032621455587499) {
   out_1847032621455587499[0] = state[6];
   out_1847032621455587499[1] = state[7];
   out_1847032621455587499[2] = state[8];
}
void H_14(double *state, double *unused, double *out_117670575450509462) {
   out_117670575450509462[0] = 0;
   out_117670575450509462[1] = 0;
   out_117670575450509462[2] = 0;
   out_117670575450509462[3] = 0;
   out_117670575450509462[4] = 0;
   out_117670575450509462[5] = 0;
   out_117670575450509462[6] = 1;
   out_117670575450509462[7] = 0;
   out_117670575450509462[8] = 0;
   out_117670575450509462[9] = 0;
   out_117670575450509462[10] = 0;
   out_117670575450509462[11] = 0;
   out_117670575450509462[12] = 0;
   out_117670575450509462[13] = 0;
   out_117670575450509462[14] = 0;
   out_117670575450509462[15] = 0;
   out_117670575450509462[16] = 0;
   out_117670575450509462[17] = 0;
   out_117670575450509462[18] = 0;
   out_117670575450509462[19] = 0;
   out_117670575450509462[20] = 0;
   out_117670575450509462[21] = 0;
   out_117670575450509462[22] = 0;
   out_117670575450509462[23] = 0;
   out_117670575450509462[24] = 0;
   out_117670575450509462[25] = 1;
   out_117670575450509462[26] = 0;
   out_117670575450509462[27] = 0;
   out_117670575450509462[28] = 0;
   out_117670575450509462[29] = 0;
   out_117670575450509462[30] = 0;
   out_117670575450509462[31] = 0;
   out_117670575450509462[32] = 0;
   out_117670575450509462[33] = 0;
   out_117670575450509462[34] = 0;
   out_117670575450509462[35] = 0;
   out_117670575450509462[36] = 0;
   out_117670575450509462[37] = 0;
   out_117670575450509462[38] = 0;
   out_117670575450509462[39] = 0;
   out_117670575450509462[40] = 0;
   out_117670575450509462[41] = 0;
   out_117670575450509462[42] = 0;
   out_117670575450509462[43] = 0;
   out_117670575450509462[44] = 1;
   out_117670575450509462[45] = 0;
   out_117670575450509462[46] = 0;
   out_117670575450509462[47] = 0;
   out_117670575450509462[48] = 0;
   out_117670575450509462[49] = 0;
   out_117670575450509462[50] = 0;
   out_117670575450509462[51] = 0;
   out_117670575450509462[52] = 0;
   out_117670575450509462[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5867685499485526905) {
  err_fun(nom_x, delta_x, out_5867685499485526905);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7496427572072330735) {
  inv_err_fun(nom_x, true_x, out_7496427572072330735);
}
void pose_H_mod_fun(double *state, double *out_4599731282943687674) {
  H_mod_fun(state, out_4599731282943687674);
}
void pose_f_fun(double *state, double dt, double *out_8448766243959956852) {
  f_fun(state,  dt, out_8448766243959956852);
}
void pose_F_fun(double *state, double dt, double *out_3524034210859456461) {
  F_fun(state,  dt, out_3524034210859456461);
}
void pose_h_4(double *state, double *unused, double *out_1468084297579901706) {
  h_4(state, unused, out_1468084297579901706);
}
void pose_H_4(double *state, double *unused, double *out_552787102095393061) {
  H_4(state, unused, out_552787102095393061);
}
void pose_h_10(double *state, double *unused, double *out_1051779536617211070) {
  h_10(state, unused, out_1051779536617211070);
}
void pose_H_10(double *state, double *unused, double *out_7440841037325716699) {
  H_10(state, unused, out_7440841037325716699);
}
void pose_h_13(double *state, double *unused, double *out_4266757043601180240) {
  h_13(state, unused, out_4266757043601180240);
}
void pose_H_13(double *state, double *unused, double *out_3765060927427725862) {
  H_13(state, unused, out_3765060927427725862);
}
void pose_h_14(double *state, double *unused, double *out_1847032621455587499) {
  h_14(state, unused, out_1847032621455587499);
}
void pose_H_14(double *state, double *unused, double *out_117670575450509462) {
  H_14(state, unused, out_117670575450509462);
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
