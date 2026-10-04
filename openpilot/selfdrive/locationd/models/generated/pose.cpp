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
void err_fun(double *nom_x, double *delta_x, double *out_932967681042200213) {
   out_932967681042200213[0] = delta_x[0] + nom_x[0];
   out_932967681042200213[1] = delta_x[1] + nom_x[1];
   out_932967681042200213[2] = delta_x[2] + nom_x[2];
   out_932967681042200213[3] = delta_x[3] + nom_x[3];
   out_932967681042200213[4] = delta_x[4] + nom_x[4];
   out_932967681042200213[5] = delta_x[5] + nom_x[5];
   out_932967681042200213[6] = delta_x[6] + nom_x[6];
   out_932967681042200213[7] = delta_x[7] + nom_x[7];
   out_932967681042200213[8] = delta_x[8] + nom_x[8];
   out_932967681042200213[9] = delta_x[9] + nom_x[9];
   out_932967681042200213[10] = delta_x[10] + nom_x[10];
   out_932967681042200213[11] = delta_x[11] + nom_x[11];
   out_932967681042200213[12] = delta_x[12] + nom_x[12];
   out_932967681042200213[13] = delta_x[13] + nom_x[13];
   out_932967681042200213[14] = delta_x[14] + nom_x[14];
   out_932967681042200213[15] = delta_x[15] + nom_x[15];
   out_932967681042200213[16] = delta_x[16] + nom_x[16];
   out_932967681042200213[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3534086283432917024) {
   out_3534086283432917024[0] = -nom_x[0] + true_x[0];
   out_3534086283432917024[1] = -nom_x[1] + true_x[1];
   out_3534086283432917024[2] = -nom_x[2] + true_x[2];
   out_3534086283432917024[3] = -nom_x[3] + true_x[3];
   out_3534086283432917024[4] = -nom_x[4] + true_x[4];
   out_3534086283432917024[5] = -nom_x[5] + true_x[5];
   out_3534086283432917024[6] = -nom_x[6] + true_x[6];
   out_3534086283432917024[7] = -nom_x[7] + true_x[7];
   out_3534086283432917024[8] = -nom_x[8] + true_x[8];
   out_3534086283432917024[9] = -nom_x[9] + true_x[9];
   out_3534086283432917024[10] = -nom_x[10] + true_x[10];
   out_3534086283432917024[11] = -nom_x[11] + true_x[11];
   out_3534086283432917024[12] = -nom_x[12] + true_x[12];
   out_3534086283432917024[13] = -nom_x[13] + true_x[13];
   out_3534086283432917024[14] = -nom_x[14] + true_x[14];
   out_3534086283432917024[15] = -nom_x[15] + true_x[15];
   out_3534086283432917024[16] = -nom_x[16] + true_x[16];
   out_3534086283432917024[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1261648596307961615) {
   out_1261648596307961615[0] = 1.0;
   out_1261648596307961615[1] = 0.0;
   out_1261648596307961615[2] = 0.0;
   out_1261648596307961615[3] = 0.0;
   out_1261648596307961615[4] = 0.0;
   out_1261648596307961615[5] = 0.0;
   out_1261648596307961615[6] = 0.0;
   out_1261648596307961615[7] = 0.0;
   out_1261648596307961615[8] = 0.0;
   out_1261648596307961615[9] = 0.0;
   out_1261648596307961615[10] = 0.0;
   out_1261648596307961615[11] = 0.0;
   out_1261648596307961615[12] = 0.0;
   out_1261648596307961615[13] = 0.0;
   out_1261648596307961615[14] = 0.0;
   out_1261648596307961615[15] = 0.0;
   out_1261648596307961615[16] = 0.0;
   out_1261648596307961615[17] = 0.0;
   out_1261648596307961615[18] = 0.0;
   out_1261648596307961615[19] = 1.0;
   out_1261648596307961615[20] = 0.0;
   out_1261648596307961615[21] = 0.0;
   out_1261648596307961615[22] = 0.0;
   out_1261648596307961615[23] = 0.0;
   out_1261648596307961615[24] = 0.0;
   out_1261648596307961615[25] = 0.0;
   out_1261648596307961615[26] = 0.0;
   out_1261648596307961615[27] = 0.0;
   out_1261648596307961615[28] = 0.0;
   out_1261648596307961615[29] = 0.0;
   out_1261648596307961615[30] = 0.0;
   out_1261648596307961615[31] = 0.0;
   out_1261648596307961615[32] = 0.0;
   out_1261648596307961615[33] = 0.0;
   out_1261648596307961615[34] = 0.0;
   out_1261648596307961615[35] = 0.0;
   out_1261648596307961615[36] = 0.0;
   out_1261648596307961615[37] = 0.0;
   out_1261648596307961615[38] = 1.0;
   out_1261648596307961615[39] = 0.0;
   out_1261648596307961615[40] = 0.0;
   out_1261648596307961615[41] = 0.0;
   out_1261648596307961615[42] = 0.0;
   out_1261648596307961615[43] = 0.0;
   out_1261648596307961615[44] = 0.0;
   out_1261648596307961615[45] = 0.0;
   out_1261648596307961615[46] = 0.0;
   out_1261648596307961615[47] = 0.0;
   out_1261648596307961615[48] = 0.0;
   out_1261648596307961615[49] = 0.0;
   out_1261648596307961615[50] = 0.0;
   out_1261648596307961615[51] = 0.0;
   out_1261648596307961615[52] = 0.0;
   out_1261648596307961615[53] = 0.0;
   out_1261648596307961615[54] = 0.0;
   out_1261648596307961615[55] = 0.0;
   out_1261648596307961615[56] = 0.0;
   out_1261648596307961615[57] = 1.0;
   out_1261648596307961615[58] = 0.0;
   out_1261648596307961615[59] = 0.0;
   out_1261648596307961615[60] = 0.0;
   out_1261648596307961615[61] = 0.0;
   out_1261648596307961615[62] = 0.0;
   out_1261648596307961615[63] = 0.0;
   out_1261648596307961615[64] = 0.0;
   out_1261648596307961615[65] = 0.0;
   out_1261648596307961615[66] = 0.0;
   out_1261648596307961615[67] = 0.0;
   out_1261648596307961615[68] = 0.0;
   out_1261648596307961615[69] = 0.0;
   out_1261648596307961615[70] = 0.0;
   out_1261648596307961615[71] = 0.0;
   out_1261648596307961615[72] = 0.0;
   out_1261648596307961615[73] = 0.0;
   out_1261648596307961615[74] = 0.0;
   out_1261648596307961615[75] = 0.0;
   out_1261648596307961615[76] = 1.0;
   out_1261648596307961615[77] = 0.0;
   out_1261648596307961615[78] = 0.0;
   out_1261648596307961615[79] = 0.0;
   out_1261648596307961615[80] = 0.0;
   out_1261648596307961615[81] = 0.0;
   out_1261648596307961615[82] = 0.0;
   out_1261648596307961615[83] = 0.0;
   out_1261648596307961615[84] = 0.0;
   out_1261648596307961615[85] = 0.0;
   out_1261648596307961615[86] = 0.0;
   out_1261648596307961615[87] = 0.0;
   out_1261648596307961615[88] = 0.0;
   out_1261648596307961615[89] = 0.0;
   out_1261648596307961615[90] = 0.0;
   out_1261648596307961615[91] = 0.0;
   out_1261648596307961615[92] = 0.0;
   out_1261648596307961615[93] = 0.0;
   out_1261648596307961615[94] = 0.0;
   out_1261648596307961615[95] = 1.0;
   out_1261648596307961615[96] = 0.0;
   out_1261648596307961615[97] = 0.0;
   out_1261648596307961615[98] = 0.0;
   out_1261648596307961615[99] = 0.0;
   out_1261648596307961615[100] = 0.0;
   out_1261648596307961615[101] = 0.0;
   out_1261648596307961615[102] = 0.0;
   out_1261648596307961615[103] = 0.0;
   out_1261648596307961615[104] = 0.0;
   out_1261648596307961615[105] = 0.0;
   out_1261648596307961615[106] = 0.0;
   out_1261648596307961615[107] = 0.0;
   out_1261648596307961615[108] = 0.0;
   out_1261648596307961615[109] = 0.0;
   out_1261648596307961615[110] = 0.0;
   out_1261648596307961615[111] = 0.0;
   out_1261648596307961615[112] = 0.0;
   out_1261648596307961615[113] = 0.0;
   out_1261648596307961615[114] = 1.0;
   out_1261648596307961615[115] = 0.0;
   out_1261648596307961615[116] = 0.0;
   out_1261648596307961615[117] = 0.0;
   out_1261648596307961615[118] = 0.0;
   out_1261648596307961615[119] = 0.0;
   out_1261648596307961615[120] = 0.0;
   out_1261648596307961615[121] = 0.0;
   out_1261648596307961615[122] = 0.0;
   out_1261648596307961615[123] = 0.0;
   out_1261648596307961615[124] = 0.0;
   out_1261648596307961615[125] = 0.0;
   out_1261648596307961615[126] = 0.0;
   out_1261648596307961615[127] = 0.0;
   out_1261648596307961615[128] = 0.0;
   out_1261648596307961615[129] = 0.0;
   out_1261648596307961615[130] = 0.0;
   out_1261648596307961615[131] = 0.0;
   out_1261648596307961615[132] = 0.0;
   out_1261648596307961615[133] = 1.0;
   out_1261648596307961615[134] = 0.0;
   out_1261648596307961615[135] = 0.0;
   out_1261648596307961615[136] = 0.0;
   out_1261648596307961615[137] = 0.0;
   out_1261648596307961615[138] = 0.0;
   out_1261648596307961615[139] = 0.0;
   out_1261648596307961615[140] = 0.0;
   out_1261648596307961615[141] = 0.0;
   out_1261648596307961615[142] = 0.0;
   out_1261648596307961615[143] = 0.0;
   out_1261648596307961615[144] = 0.0;
   out_1261648596307961615[145] = 0.0;
   out_1261648596307961615[146] = 0.0;
   out_1261648596307961615[147] = 0.0;
   out_1261648596307961615[148] = 0.0;
   out_1261648596307961615[149] = 0.0;
   out_1261648596307961615[150] = 0.0;
   out_1261648596307961615[151] = 0.0;
   out_1261648596307961615[152] = 1.0;
   out_1261648596307961615[153] = 0.0;
   out_1261648596307961615[154] = 0.0;
   out_1261648596307961615[155] = 0.0;
   out_1261648596307961615[156] = 0.0;
   out_1261648596307961615[157] = 0.0;
   out_1261648596307961615[158] = 0.0;
   out_1261648596307961615[159] = 0.0;
   out_1261648596307961615[160] = 0.0;
   out_1261648596307961615[161] = 0.0;
   out_1261648596307961615[162] = 0.0;
   out_1261648596307961615[163] = 0.0;
   out_1261648596307961615[164] = 0.0;
   out_1261648596307961615[165] = 0.0;
   out_1261648596307961615[166] = 0.0;
   out_1261648596307961615[167] = 0.0;
   out_1261648596307961615[168] = 0.0;
   out_1261648596307961615[169] = 0.0;
   out_1261648596307961615[170] = 0.0;
   out_1261648596307961615[171] = 1.0;
   out_1261648596307961615[172] = 0.0;
   out_1261648596307961615[173] = 0.0;
   out_1261648596307961615[174] = 0.0;
   out_1261648596307961615[175] = 0.0;
   out_1261648596307961615[176] = 0.0;
   out_1261648596307961615[177] = 0.0;
   out_1261648596307961615[178] = 0.0;
   out_1261648596307961615[179] = 0.0;
   out_1261648596307961615[180] = 0.0;
   out_1261648596307961615[181] = 0.0;
   out_1261648596307961615[182] = 0.0;
   out_1261648596307961615[183] = 0.0;
   out_1261648596307961615[184] = 0.0;
   out_1261648596307961615[185] = 0.0;
   out_1261648596307961615[186] = 0.0;
   out_1261648596307961615[187] = 0.0;
   out_1261648596307961615[188] = 0.0;
   out_1261648596307961615[189] = 0.0;
   out_1261648596307961615[190] = 1.0;
   out_1261648596307961615[191] = 0.0;
   out_1261648596307961615[192] = 0.0;
   out_1261648596307961615[193] = 0.0;
   out_1261648596307961615[194] = 0.0;
   out_1261648596307961615[195] = 0.0;
   out_1261648596307961615[196] = 0.0;
   out_1261648596307961615[197] = 0.0;
   out_1261648596307961615[198] = 0.0;
   out_1261648596307961615[199] = 0.0;
   out_1261648596307961615[200] = 0.0;
   out_1261648596307961615[201] = 0.0;
   out_1261648596307961615[202] = 0.0;
   out_1261648596307961615[203] = 0.0;
   out_1261648596307961615[204] = 0.0;
   out_1261648596307961615[205] = 0.0;
   out_1261648596307961615[206] = 0.0;
   out_1261648596307961615[207] = 0.0;
   out_1261648596307961615[208] = 0.0;
   out_1261648596307961615[209] = 1.0;
   out_1261648596307961615[210] = 0.0;
   out_1261648596307961615[211] = 0.0;
   out_1261648596307961615[212] = 0.0;
   out_1261648596307961615[213] = 0.0;
   out_1261648596307961615[214] = 0.0;
   out_1261648596307961615[215] = 0.0;
   out_1261648596307961615[216] = 0.0;
   out_1261648596307961615[217] = 0.0;
   out_1261648596307961615[218] = 0.0;
   out_1261648596307961615[219] = 0.0;
   out_1261648596307961615[220] = 0.0;
   out_1261648596307961615[221] = 0.0;
   out_1261648596307961615[222] = 0.0;
   out_1261648596307961615[223] = 0.0;
   out_1261648596307961615[224] = 0.0;
   out_1261648596307961615[225] = 0.0;
   out_1261648596307961615[226] = 0.0;
   out_1261648596307961615[227] = 0.0;
   out_1261648596307961615[228] = 1.0;
   out_1261648596307961615[229] = 0.0;
   out_1261648596307961615[230] = 0.0;
   out_1261648596307961615[231] = 0.0;
   out_1261648596307961615[232] = 0.0;
   out_1261648596307961615[233] = 0.0;
   out_1261648596307961615[234] = 0.0;
   out_1261648596307961615[235] = 0.0;
   out_1261648596307961615[236] = 0.0;
   out_1261648596307961615[237] = 0.0;
   out_1261648596307961615[238] = 0.0;
   out_1261648596307961615[239] = 0.0;
   out_1261648596307961615[240] = 0.0;
   out_1261648596307961615[241] = 0.0;
   out_1261648596307961615[242] = 0.0;
   out_1261648596307961615[243] = 0.0;
   out_1261648596307961615[244] = 0.0;
   out_1261648596307961615[245] = 0.0;
   out_1261648596307961615[246] = 0.0;
   out_1261648596307961615[247] = 1.0;
   out_1261648596307961615[248] = 0.0;
   out_1261648596307961615[249] = 0.0;
   out_1261648596307961615[250] = 0.0;
   out_1261648596307961615[251] = 0.0;
   out_1261648596307961615[252] = 0.0;
   out_1261648596307961615[253] = 0.0;
   out_1261648596307961615[254] = 0.0;
   out_1261648596307961615[255] = 0.0;
   out_1261648596307961615[256] = 0.0;
   out_1261648596307961615[257] = 0.0;
   out_1261648596307961615[258] = 0.0;
   out_1261648596307961615[259] = 0.0;
   out_1261648596307961615[260] = 0.0;
   out_1261648596307961615[261] = 0.0;
   out_1261648596307961615[262] = 0.0;
   out_1261648596307961615[263] = 0.0;
   out_1261648596307961615[264] = 0.0;
   out_1261648596307961615[265] = 0.0;
   out_1261648596307961615[266] = 1.0;
   out_1261648596307961615[267] = 0.0;
   out_1261648596307961615[268] = 0.0;
   out_1261648596307961615[269] = 0.0;
   out_1261648596307961615[270] = 0.0;
   out_1261648596307961615[271] = 0.0;
   out_1261648596307961615[272] = 0.0;
   out_1261648596307961615[273] = 0.0;
   out_1261648596307961615[274] = 0.0;
   out_1261648596307961615[275] = 0.0;
   out_1261648596307961615[276] = 0.0;
   out_1261648596307961615[277] = 0.0;
   out_1261648596307961615[278] = 0.0;
   out_1261648596307961615[279] = 0.0;
   out_1261648596307961615[280] = 0.0;
   out_1261648596307961615[281] = 0.0;
   out_1261648596307961615[282] = 0.0;
   out_1261648596307961615[283] = 0.0;
   out_1261648596307961615[284] = 0.0;
   out_1261648596307961615[285] = 1.0;
   out_1261648596307961615[286] = 0.0;
   out_1261648596307961615[287] = 0.0;
   out_1261648596307961615[288] = 0.0;
   out_1261648596307961615[289] = 0.0;
   out_1261648596307961615[290] = 0.0;
   out_1261648596307961615[291] = 0.0;
   out_1261648596307961615[292] = 0.0;
   out_1261648596307961615[293] = 0.0;
   out_1261648596307961615[294] = 0.0;
   out_1261648596307961615[295] = 0.0;
   out_1261648596307961615[296] = 0.0;
   out_1261648596307961615[297] = 0.0;
   out_1261648596307961615[298] = 0.0;
   out_1261648596307961615[299] = 0.0;
   out_1261648596307961615[300] = 0.0;
   out_1261648596307961615[301] = 0.0;
   out_1261648596307961615[302] = 0.0;
   out_1261648596307961615[303] = 0.0;
   out_1261648596307961615[304] = 1.0;
   out_1261648596307961615[305] = 0.0;
   out_1261648596307961615[306] = 0.0;
   out_1261648596307961615[307] = 0.0;
   out_1261648596307961615[308] = 0.0;
   out_1261648596307961615[309] = 0.0;
   out_1261648596307961615[310] = 0.0;
   out_1261648596307961615[311] = 0.0;
   out_1261648596307961615[312] = 0.0;
   out_1261648596307961615[313] = 0.0;
   out_1261648596307961615[314] = 0.0;
   out_1261648596307961615[315] = 0.0;
   out_1261648596307961615[316] = 0.0;
   out_1261648596307961615[317] = 0.0;
   out_1261648596307961615[318] = 0.0;
   out_1261648596307961615[319] = 0.0;
   out_1261648596307961615[320] = 0.0;
   out_1261648596307961615[321] = 0.0;
   out_1261648596307961615[322] = 0.0;
   out_1261648596307961615[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6850450012256179975) {
   out_6850450012256179975[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6850450012256179975[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6850450012256179975[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6850450012256179975[3] = dt*state[12] + state[3];
   out_6850450012256179975[4] = dt*state[13] + state[4];
   out_6850450012256179975[5] = dt*state[14] + state[5];
   out_6850450012256179975[6] = state[6];
   out_6850450012256179975[7] = state[7];
   out_6850450012256179975[8] = state[8];
   out_6850450012256179975[9] = state[9];
   out_6850450012256179975[10] = state[10];
   out_6850450012256179975[11] = state[11];
   out_6850450012256179975[12] = state[12];
   out_6850450012256179975[13] = state[13];
   out_6850450012256179975[14] = state[14];
   out_6850450012256179975[15] = state[15];
   out_6850450012256179975[16] = state[16];
   out_6850450012256179975[17] = state[17];
}
void F_fun(double *state, double dt, double *out_139005871191941126) {
   out_139005871191941126[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_139005871191941126[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_139005871191941126[2] = 0;
   out_139005871191941126[3] = 0;
   out_139005871191941126[4] = 0;
   out_139005871191941126[5] = 0;
   out_139005871191941126[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_139005871191941126[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_139005871191941126[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_139005871191941126[9] = 0;
   out_139005871191941126[10] = 0;
   out_139005871191941126[11] = 0;
   out_139005871191941126[12] = 0;
   out_139005871191941126[13] = 0;
   out_139005871191941126[14] = 0;
   out_139005871191941126[15] = 0;
   out_139005871191941126[16] = 0;
   out_139005871191941126[17] = 0;
   out_139005871191941126[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_139005871191941126[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_139005871191941126[20] = 0;
   out_139005871191941126[21] = 0;
   out_139005871191941126[22] = 0;
   out_139005871191941126[23] = 0;
   out_139005871191941126[24] = 0;
   out_139005871191941126[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_139005871191941126[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_139005871191941126[27] = 0;
   out_139005871191941126[28] = 0;
   out_139005871191941126[29] = 0;
   out_139005871191941126[30] = 0;
   out_139005871191941126[31] = 0;
   out_139005871191941126[32] = 0;
   out_139005871191941126[33] = 0;
   out_139005871191941126[34] = 0;
   out_139005871191941126[35] = 0;
   out_139005871191941126[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_139005871191941126[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_139005871191941126[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_139005871191941126[39] = 0;
   out_139005871191941126[40] = 0;
   out_139005871191941126[41] = 0;
   out_139005871191941126[42] = 0;
   out_139005871191941126[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_139005871191941126[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_139005871191941126[45] = 0;
   out_139005871191941126[46] = 0;
   out_139005871191941126[47] = 0;
   out_139005871191941126[48] = 0;
   out_139005871191941126[49] = 0;
   out_139005871191941126[50] = 0;
   out_139005871191941126[51] = 0;
   out_139005871191941126[52] = 0;
   out_139005871191941126[53] = 0;
   out_139005871191941126[54] = 0;
   out_139005871191941126[55] = 0;
   out_139005871191941126[56] = 0;
   out_139005871191941126[57] = 1;
   out_139005871191941126[58] = 0;
   out_139005871191941126[59] = 0;
   out_139005871191941126[60] = 0;
   out_139005871191941126[61] = 0;
   out_139005871191941126[62] = 0;
   out_139005871191941126[63] = 0;
   out_139005871191941126[64] = 0;
   out_139005871191941126[65] = 0;
   out_139005871191941126[66] = dt;
   out_139005871191941126[67] = 0;
   out_139005871191941126[68] = 0;
   out_139005871191941126[69] = 0;
   out_139005871191941126[70] = 0;
   out_139005871191941126[71] = 0;
   out_139005871191941126[72] = 0;
   out_139005871191941126[73] = 0;
   out_139005871191941126[74] = 0;
   out_139005871191941126[75] = 0;
   out_139005871191941126[76] = 1;
   out_139005871191941126[77] = 0;
   out_139005871191941126[78] = 0;
   out_139005871191941126[79] = 0;
   out_139005871191941126[80] = 0;
   out_139005871191941126[81] = 0;
   out_139005871191941126[82] = 0;
   out_139005871191941126[83] = 0;
   out_139005871191941126[84] = 0;
   out_139005871191941126[85] = dt;
   out_139005871191941126[86] = 0;
   out_139005871191941126[87] = 0;
   out_139005871191941126[88] = 0;
   out_139005871191941126[89] = 0;
   out_139005871191941126[90] = 0;
   out_139005871191941126[91] = 0;
   out_139005871191941126[92] = 0;
   out_139005871191941126[93] = 0;
   out_139005871191941126[94] = 0;
   out_139005871191941126[95] = 1;
   out_139005871191941126[96] = 0;
   out_139005871191941126[97] = 0;
   out_139005871191941126[98] = 0;
   out_139005871191941126[99] = 0;
   out_139005871191941126[100] = 0;
   out_139005871191941126[101] = 0;
   out_139005871191941126[102] = 0;
   out_139005871191941126[103] = 0;
   out_139005871191941126[104] = dt;
   out_139005871191941126[105] = 0;
   out_139005871191941126[106] = 0;
   out_139005871191941126[107] = 0;
   out_139005871191941126[108] = 0;
   out_139005871191941126[109] = 0;
   out_139005871191941126[110] = 0;
   out_139005871191941126[111] = 0;
   out_139005871191941126[112] = 0;
   out_139005871191941126[113] = 0;
   out_139005871191941126[114] = 1;
   out_139005871191941126[115] = 0;
   out_139005871191941126[116] = 0;
   out_139005871191941126[117] = 0;
   out_139005871191941126[118] = 0;
   out_139005871191941126[119] = 0;
   out_139005871191941126[120] = 0;
   out_139005871191941126[121] = 0;
   out_139005871191941126[122] = 0;
   out_139005871191941126[123] = 0;
   out_139005871191941126[124] = 0;
   out_139005871191941126[125] = 0;
   out_139005871191941126[126] = 0;
   out_139005871191941126[127] = 0;
   out_139005871191941126[128] = 0;
   out_139005871191941126[129] = 0;
   out_139005871191941126[130] = 0;
   out_139005871191941126[131] = 0;
   out_139005871191941126[132] = 0;
   out_139005871191941126[133] = 1;
   out_139005871191941126[134] = 0;
   out_139005871191941126[135] = 0;
   out_139005871191941126[136] = 0;
   out_139005871191941126[137] = 0;
   out_139005871191941126[138] = 0;
   out_139005871191941126[139] = 0;
   out_139005871191941126[140] = 0;
   out_139005871191941126[141] = 0;
   out_139005871191941126[142] = 0;
   out_139005871191941126[143] = 0;
   out_139005871191941126[144] = 0;
   out_139005871191941126[145] = 0;
   out_139005871191941126[146] = 0;
   out_139005871191941126[147] = 0;
   out_139005871191941126[148] = 0;
   out_139005871191941126[149] = 0;
   out_139005871191941126[150] = 0;
   out_139005871191941126[151] = 0;
   out_139005871191941126[152] = 1;
   out_139005871191941126[153] = 0;
   out_139005871191941126[154] = 0;
   out_139005871191941126[155] = 0;
   out_139005871191941126[156] = 0;
   out_139005871191941126[157] = 0;
   out_139005871191941126[158] = 0;
   out_139005871191941126[159] = 0;
   out_139005871191941126[160] = 0;
   out_139005871191941126[161] = 0;
   out_139005871191941126[162] = 0;
   out_139005871191941126[163] = 0;
   out_139005871191941126[164] = 0;
   out_139005871191941126[165] = 0;
   out_139005871191941126[166] = 0;
   out_139005871191941126[167] = 0;
   out_139005871191941126[168] = 0;
   out_139005871191941126[169] = 0;
   out_139005871191941126[170] = 0;
   out_139005871191941126[171] = 1;
   out_139005871191941126[172] = 0;
   out_139005871191941126[173] = 0;
   out_139005871191941126[174] = 0;
   out_139005871191941126[175] = 0;
   out_139005871191941126[176] = 0;
   out_139005871191941126[177] = 0;
   out_139005871191941126[178] = 0;
   out_139005871191941126[179] = 0;
   out_139005871191941126[180] = 0;
   out_139005871191941126[181] = 0;
   out_139005871191941126[182] = 0;
   out_139005871191941126[183] = 0;
   out_139005871191941126[184] = 0;
   out_139005871191941126[185] = 0;
   out_139005871191941126[186] = 0;
   out_139005871191941126[187] = 0;
   out_139005871191941126[188] = 0;
   out_139005871191941126[189] = 0;
   out_139005871191941126[190] = 1;
   out_139005871191941126[191] = 0;
   out_139005871191941126[192] = 0;
   out_139005871191941126[193] = 0;
   out_139005871191941126[194] = 0;
   out_139005871191941126[195] = 0;
   out_139005871191941126[196] = 0;
   out_139005871191941126[197] = 0;
   out_139005871191941126[198] = 0;
   out_139005871191941126[199] = 0;
   out_139005871191941126[200] = 0;
   out_139005871191941126[201] = 0;
   out_139005871191941126[202] = 0;
   out_139005871191941126[203] = 0;
   out_139005871191941126[204] = 0;
   out_139005871191941126[205] = 0;
   out_139005871191941126[206] = 0;
   out_139005871191941126[207] = 0;
   out_139005871191941126[208] = 0;
   out_139005871191941126[209] = 1;
   out_139005871191941126[210] = 0;
   out_139005871191941126[211] = 0;
   out_139005871191941126[212] = 0;
   out_139005871191941126[213] = 0;
   out_139005871191941126[214] = 0;
   out_139005871191941126[215] = 0;
   out_139005871191941126[216] = 0;
   out_139005871191941126[217] = 0;
   out_139005871191941126[218] = 0;
   out_139005871191941126[219] = 0;
   out_139005871191941126[220] = 0;
   out_139005871191941126[221] = 0;
   out_139005871191941126[222] = 0;
   out_139005871191941126[223] = 0;
   out_139005871191941126[224] = 0;
   out_139005871191941126[225] = 0;
   out_139005871191941126[226] = 0;
   out_139005871191941126[227] = 0;
   out_139005871191941126[228] = 1;
   out_139005871191941126[229] = 0;
   out_139005871191941126[230] = 0;
   out_139005871191941126[231] = 0;
   out_139005871191941126[232] = 0;
   out_139005871191941126[233] = 0;
   out_139005871191941126[234] = 0;
   out_139005871191941126[235] = 0;
   out_139005871191941126[236] = 0;
   out_139005871191941126[237] = 0;
   out_139005871191941126[238] = 0;
   out_139005871191941126[239] = 0;
   out_139005871191941126[240] = 0;
   out_139005871191941126[241] = 0;
   out_139005871191941126[242] = 0;
   out_139005871191941126[243] = 0;
   out_139005871191941126[244] = 0;
   out_139005871191941126[245] = 0;
   out_139005871191941126[246] = 0;
   out_139005871191941126[247] = 1;
   out_139005871191941126[248] = 0;
   out_139005871191941126[249] = 0;
   out_139005871191941126[250] = 0;
   out_139005871191941126[251] = 0;
   out_139005871191941126[252] = 0;
   out_139005871191941126[253] = 0;
   out_139005871191941126[254] = 0;
   out_139005871191941126[255] = 0;
   out_139005871191941126[256] = 0;
   out_139005871191941126[257] = 0;
   out_139005871191941126[258] = 0;
   out_139005871191941126[259] = 0;
   out_139005871191941126[260] = 0;
   out_139005871191941126[261] = 0;
   out_139005871191941126[262] = 0;
   out_139005871191941126[263] = 0;
   out_139005871191941126[264] = 0;
   out_139005871191941126[265] = 0;
   out_139005871191941126[266] = 1;
   out_139005871191941126[267] = 0;
   out_139005871191941126[268] = 0;
   out_139005871191941126[269] = 0;
   out_139005871191941126[270] = 0;
   out_139005871191941126[271] = 0;
   out_139005871191941126[272] = 0;
   out_139005871191941126[273] = 0;
   out_139005871191941126[274] = 0;
   out_139005871191941126[275] = 0;
   out_139005871191941126[276] = 0;
   out_139005871191941126[277] = 0;
   out_139005871191941126[278] = 0;
   out_139005871191941126[279] = 0;
   out_139005871191941126[280] = 0;
   out_139005871191941126[281] = 0;
   out_139005871191941126[282] = 0;
   out_139005871191941126[283] = 0;
   out_139005871191941126[284] = 0;
   out_139005871191941126[285] = 1;
   out_139005871191941126[286] = 0;
   out_139005871191941126[287] = 0;
   out_139005871191941126[288] = 0;
   out_139005871191941126[289] = 0;
   out_139005871191941126[290] = 0;
   out_139005871191941126[291] = 0;
   out_139005871191941126[292] = 0;
   out_139005871191941126[293] = 0;
   out_139005871191941126[294] = 0;
   out_139005871191941126[295] = 0;
   out_139005871191941126[296] = 0;
   out_139005871191941126[297] = 0;
   out_139005871191941126[298] = 0;
   out_139005871191941126[299] = 0;
   out_139005871191941126[300] = 0;
   out_139005871191941126[301] = 0;
   out_139005871191941126[302] = 0;
   out_139005871191941126[303] = 0;
   out_139005871191941126[304] = 1;
   out_139005871191941126[305] = 0;
   out_139005871191941126[306] = 0;
   out_139005871191941126[307] = 0;
   out_139005871191941126[308] = 0;
   out_139005871191941126[309] = 0;
   out_139005871191941126[310] = 0;
   out_139005871191941126[311] = 0;
   out_139005871191941126[312] = 0;
   out_139005871191941126[313] = 0;
   out_139005871191941126[314] = 0;
   out_139005871191941126[315] = 0;
   out_139005871191941126[316] = 0;
   out_139005871191941126[317] = 0;
   out_139005871191941126[318] = 0;
   out_139005871191941126[319] = 0;
   out_139005871191941126[320] = 0;
   out_139005871191941126[321] = 0;
   out_139005871191941126[322] = 0;
   out_139005871191941126[323] = 1;
}
void h_4(double *state, double *unused, double *out_6584047401950888130) {
   out_6584047401950888130[0] = state[6] + state[9];
   out_6584047401950888130[1] = state[7] + state[10];
   out_6584047401950888130[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3840307253386032882) {
   out_3840307253386032882[0] = 0;
   out_3840307253386032882[1] = 0;
   out_3840307253386032882[2] = 0;
   out_3840307253386032882[3] = 0;
   out_3840307253386032882[4] = 0;
   out_3840307253386032882[5] = 0;
   out_3840307253386032882[6] = 1;
   out_3840307253386032882[7] = 0;
   out_3840307253386032882[8] = 0;
   out_3840307253386032882[9] = 1;
   out_3840307253386032882[10] = 0;
   out_3840307253386032882[11] = 0;
   out_3840307253386032882[12] = 0;
   out_3840307253386032882[13] = 0;
   out_3840307253386032882[14] = 0;
   out_3840307253386032882[15] = 0;
   out_3840307253386032882[16] = 0;
   out_3840307253386032882[17] = 0;
   out_3840307253386032882[18] = 0;
   out_3840307253386032882[19] = 0;
   out_3840307253386032882[20] = 0;
   out_3840307253386032882[21] = 0;
   out_3840307253386032882[22] = 0;
   out_3840307253386032882[23] = 0;
   out_3840307253386032882[24] = 0;
   out_3840307253386032882[25] = 1;
   out_3840307253386032882[26] = 0;
   out_3840307253386032882[27] = 0;
   out_3840307253386032882[28] = 1;
   out_3840307253386032882[29] = 0;
   out_3840307253386032882[30] = 0;
   out_3840307253386032882[31] = 0;
   out_3840307253386032882[32] = 0;
   out_3840307253386032882[33] = 0;
   out_3840307253386032882[34] = 0;
   out_3840307253386032882[35] = 0;
   out_3840307253386032882[36] = 0;
   out_3840307253386032882[37] = 0;
   out_3840307253386032882[38] = 0;
   out_3840307253386032882[39] = 0;
   out_3840307253386032882[40] = 0;
   out_3840307253386032882[41] = 0;
   out_3840307253386032882[42] = 0;
   out_3840307253386032882[43] = 0;
   out_3840307253386032882[44] = 1;
   out_3840307253386032882[45] = 0;
   out_3840307253386032882[46] = 0;
   out_3840307253386032882[47] = 1;
   out_3840307253386032882[48] = 0;
   out_3840307253386032882[49] = 0;
   out_3840307253386032882[50] = 0;
   out_3840307253386032882[51] = 0;
   out_3840307253386032882[52] = 0;
   out_3840307253386032882[53] = 0;
}
void h_10(double *state, double *unused, double *out_6356449235196377560) {
   out_6356449235196377560[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6356449235196377560[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6356449235196377560[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2411644251267738056) {
   out_2411644251267738056[0] = 0;
   out_2411644251267738056[1] = 9.8100000000000005*cos(state[1]);
   out_2411644251267738056[2] = 0;
   out_2411644251267738056[3] = 0;
   out_2411644251267738056[4] = -state[8];
   out_2411644251267738056[5] = state[7];
   out_2411644251267738056[6] = 0;
   out_2411644251267738056[7] = state[5];
   out_2411644251267738056[8] = -state[4];
   out_2411644251267738056[9] = 0;
   out_2411644251267738056[10] = 0;
   out_2411644251267738056[11] = 0;
   out_2411644251267738056[12] = 1;
   out_2411644251267738056[13] = 0;
   out_2411644251267738056[14] = 0;
   out_2411644251267738056[15] = 1;
   out_2411644251267738056[16] = 0;
   out_2411644251267738056[17] = 0;
   out_2411644251267738056[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2411644251267738056[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2411644251267738056[20] = 0;
   out_2411644251267738056[21] = state[8];
   out_2411644251267738056[22] = 0;
   out_2411644251267738056[23] = -state[6];
   out_2411644251267738056[24] = -state[5];
   out_2411644251267738056[25] = 0;
   out_2411644251267738056[26] = state[3];
   out_2411644251267738056[27] = 0;
   out_2411644251267738056[28] = 0;
   out_2411644251267738056[29] = 0;
   out_2411644251267738056[30] = 0;
   out_2411644251267738056[31] = 1;
   out_2411644251267738056[32] = 0;
   out_2411644251267738056[33] = 0;
   out_2411644251267738056[34] = 1;
   out_2411644251267738056[35] = 0;
   out_2411644251267738056[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2411644251267738056[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2411644251267738056[38] = 0;
   out_2411644251267738056[39] = -state[7];
   out_2411644251267738056[40] = state[6];
   out_2411644251267738056[41] = 0;
   out_2411644251267738056[42] = state[4];
   out_2411644251267738056[43] = -state[3];
   out_2411644251267738056[44] = 0;
   out_2411644251267738056[45] = 0;
   out_2411644251267738056[46] = 0;
   out_2411644251267738056[47] = 0;
   out_2411644251267738056[48] = 0;
   out_2411644251267738056[49] = 0;
   out_2411644251267738056[50] = 1;
   out_2411644251267738056[51] = 0;
   out_2411644251267738056[52] = 0;
   out_2411644251267738056[53] = 1;
}
void h_13(double *state, double *unused, double *out_8442951675068228609) {
   out_8442951675068228609[0] = state[3];
   out_8442951675068228609[1] = state[4];
   out_8442951675068228609[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6551790083508858) {
   out_6551790083508858[0] = 0;
   out_6551790083508858[1] = 0;
   out_6551790083508858[2] = 0;
   out_6551790083508858[3] = 1;
   out_6551790083508858[4] = 0;
   out_6551790083508858[5] = 0;
   out_6551790083508858[6] = 0;
   out_6551790083508858[7] = 0;
   out_6551790083508858[8] = 0;
   out_6551790083508858[9] = 0;
   out_6551790083508858[10] = 0;
   out_6551790083508858[11] = 0;
   out_6551790083508858[12] = 0;
   out_6551790083508858[13] = 0;
   out_6551790083508858[14] = 0;
   out_6551790083508858[15] = 0;
   out_6551790083508858[16] = 0;
   out_6551790083508858[17] = 0;
   out_6551790083508858[18] = 0;
   out_6551790083508858[19] = 0;
   out_6551790083508858[20] = 0;
   out_6551790083508858[21] = 0;
   out_6551790083508858[22] = 1;
   out_6551790083508858[23] = 0;
   out_6551790083508858[24] = 0;
   out_6551790083508858[25] = 0;
   out_6551790083508858[26] = 0;
   out_6551790083508858[27] = 0;
   out_6551790083508858[28] = 0;
   out_6551790083508858[29] = 0;
   out_6551790083508858[30] = 0;
   out_6551790083508858[31] = 0;
   out_6551790083508858[32] = 0;
   out_6551790083508858[33] = 0;
   out_6551790083508858[34] = 0;
   out_6551790083508858[35] = 0;
   out_6551790083508858[36] = 0;
   out_6551790083508858[37] = 0;
   out_6551790083508858[38] = 0;
   out_6551790083508858[39] = 0;
   out_6551790083508858[40] = 0;
   out_6551790083508858[41] = 1;
   out_6551790083508858[42] = 0;
   out_6551790083508858[43] = 0;
   out_6551790083508858[44] = 0;
   out_6551790083508858[45] = 0;
   out_6551790083508858[46] = 0;
   out_6551790083508858[47] = 0;
   out_6551790083508858[48] = 0;
   out_6551790083508858[49] = 0;
   out_6551790083508858[50] = 0;
   out_6551790083508858[51] = 0;
   out_6551790083508858[52] = 0;
   out_6551790083508858[53] = 0;
}
void h_14(double *state, double *unused, double *out_8458196630210230674) {
   out_8458196630210230674[0] = state[6];
   out_8458196630210230674[1] = state[7];
   out_8458196630210230674[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3640838561893707542) {
   out_3640838561893707542[0] = 0;
   out_3640838561893707542[1] = 0;
   out_3640838561893707542[2] = 0;
   out_3640838561893707542[3] = 0;
   out_3640838561893707542[4] = 0;
   out_3640838561893707542[5] = 0;
   out_3640838561893707542[6] = 1;
   out_3640838561893707542[7] = 0;
   out_3640838561893707542[8] = 0;
   out_3640838561893707542[9] = 0;
   out_3640838561893707542[10] = 0;
   out_3640838561893707542[11] = 0;
   out_3640838561893707542[12] = 0;
   out_3640838561893707542[13] = 0;
   out_3640838561893707542[14] = 0;
   out_3640838561893707542[15] = 0;
   out_3640838561893707542[16] = 0;
   out_3640838561893707542[17] = 0;
   out_3640838561893707542[18] = 0;
   out_3640838561893707542[19] = 0;
   out_3640838561893707542[20] = 0;
   out_3640838561893707542[21] = 0;
   out_3640838561893707542[22] = 0;
   out_3640838561893707542[23] = 0;
   out_3640838561893707542[24] = 0;
   out_3640838561893707542[25] = 1;
   out_3640838561893707542[26] = 0;
   out_3640838561893707542[27] = 0;
   out_3640838561893707542[28] = 0;
   out_3640838561893707542[29] = 0;
   out_3640838561893707542[30] = 0;
   out_3640838561893707542[31] = 0;
   out_3640838561893707542[32] = 0;
   out_3640838561893707542[33] = 0;
   out_3640838561893707542[34] = 0;
   out_3640838561893707542[35] = 0;
   out_3640838561893707542[36] = 0;
   out_3640838561893707542[37] = 0;
   out_3640838561893707542[38] = 0;
   out_3640838561893707542[39] = 0;
   out_3640838561893707542[40] = 0;
   out_3640838561893707542[41] = 0;
   out_3640838561893707542[42] = 0;
   out_3640838561893707542[43] = 0;
   out_3640838561893707542[44] = 1;
   out_3640838561893707542[45] = 0;
   out_3640838561893707542[46] = 0;
   out_3640838561893707542[47] = 0;
   out_3640838561893707542[48] = 0;
   out_3640838561893707542[49] = 0;
   out_3640838561893707542[50] = 0;
   out_3640838561893707542[51] = 0;
   out_3640838561893707542[52] = 0;
   out_3640838561893707542[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_932967681042200213) {
  err_fun(nom_x, delta_x, out_932967681042200213);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3534086283432917024) {
  inv_err_fun(nom_x, true_x, out_3534086283432917024);
}
void pose_H_mod_fun(double *state, double *out_1261648596307961615) {
  H_mod_fun(state, out_1261648596307961615);
}
void pose_f_fun(double *state, double dt, double *out_6850450012256179975) {
  f_fun(state,  dt, out_6850450012256179975);
}
void pose_F_fun(double *state, double dt, double *out_139005871191941126) {
  F_fun(state,  dt, out_139005871191941126);
}
void pose_h_4(double *state, double *unused, double *out_6584047401950888130) {
  h_4(state, unused, out_6584047401950888130);
}
void pose_H_4(double *state, double *unused, double *out_3840307253386032882) {
  H_4(state, unused, out_3840307253386032882);
}
void pose_h_10(double *state, double *unused, double *out_6356449235196377560) {
  h_10(state, unused, out_6356449235196377560);
}
void pose_H_10(double *state, double *unused, double *out_2411644251267738056) {
  H_10(state, unused, out_2411644251267738056);
}
void pose_h_13(double *state, double *unused, double *out_8442951675068228609) {
  h_13(state, unused, out_8442951675068228609);
}
void pose_H_13(double *state, double *unused, double *out_6551790083508858) {
  H_13(state, unused, out_6551790083508858);
}
void pose_h_14(double *state, double *unused, double *out_8458196630210230674) {
  h_14(state, unused, out_8458196630210230674);
}
void pose_H_14(double *state, double *unused, double *out_3640838561893707542) {
  H_14(state, unused, out_3640838561893707542);
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
