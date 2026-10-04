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
void err_fun(double *nom_x, double *delta_x, double *out_1366452659282605760) {
   out_1366452659282605760[0] = delta_x[0] + nom_x[0];
   out_1366452659282605760[1] = delta_x[1] + nom_x[1];
   out_1366452659282605760[2] = delta_x[2] + nom_x[2];
   out_1366452659282605760[3] = delta_x[3] + nom_x[3];
   out_1366452659282605760[4] = delta_x[4] + nom_x[4];
   out_1366452659282605760[5] = delta_x[5] + nom_x[5];
   out_1366452659282605760[6] = delta_x[6] + nom_x[6];
   out_1366452659282605760[7] = delta_x[7] + nom_x[7];
   out_1366452659282605760[8] = delta_x[8] + nom_x[8];
   out_1366452659282605760[9] = delta_x[9] + nom_x[9];
   out_1366452659282605760[10] = delta_x[10] + nom_x[10];
   out_1366452659282605760[11] = delta_x[11] + nom_x[11];
   out_1366452659282605760[12] = delta_x[12] + nom_x[12];
   out_1366452659282605760[13] = delta_x[13] + nom_x[13];
   out_1366452659282605760[14] = delta_x[14] + nom_x[14];
   out_1366452659282605760[15] = delta_x[15] + nom_x[15];
   out_1366452659282605760[16] = delta_x[16] + nom_x[16];
   out_1366452659282605760[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_633665134700440095) {
   out_633665134700440095[0] = -nom_x[0] + true_x[0];
   out_633665134700440095[1] = -nom_x[1] + true_x[1];
   out_633665134700440095[2] = -nom_x[2] + true_x[2];
   out_633665134700440095[3] = -nom_x[3] + true_x[3];
   out_633665134700440095[4] = -nom_x[4] + true_x[4];
   out_633665134700440095[5] = -nom_x[5] + true_x[5];
   out_633665134700440095[6] = -nom_x[6] + true_x[6];
   out_633665134700440095[7] = -nom_x[7] + true_x[7];
   out_633665134700440095[8] = -nom_x[8] + true_x[8];
   out_633665134700440095[9] = -nom_x[9] + true_x[9];
   out_633665134700440095[10] = -nom_x[10] + true_x[10];
   out_633665134700440095[11] = -nom_x[11] + true_x[11];
   out_633665134700440095[12] = -nom_x[12] + true_x[12];
   out_633665134700440095[13] = -nom_x[13] + true_x[13];
   out_633665134700440095[14] = -nom_x[14] + true_x[14];
   out_633665134700440095[15] = -nom_x[15] + true_x[15];
   out_633665134700440095[16] = -nom_x[16] + true_x[16];
   out_633665134700440095[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6557368431862547615) {
   out_6557368431862547615[0] = 1.0;
   out_6557368431862547615[1] = 0.0;
   out_6557368431862547615[2] = 0.0;
   out_6557368431862547615[3] = 0.0;
   out_6557368431862547615[4] = 0.0;
   out_6557368431862547615[5] = 0.0;
   out_6557368431862547615[6] = 0.0;
   out_6557368431862547615[7] = 0.0;
   out_6557368431862547615[8] = 0.0;
   out_6557368431862547615[9] = 0.0;
   out_6557368431862547615[10] = 0.0;
   out_6557368431862547615[11] = 0.0;
   out_6557368431862547615[12] = 0.0;
   out_6557368431862547615[13] = 0.0;
   out_6557368431862547615[14] = 0.0;
   out_6557368431862547615[15] = 0.0;
   out_6557368431862547615[16] = 0.0;
   out_6557368431862547615[17] = 0.0;
   out_6557368431862547615[18] = 0.0;
   out_6557368431862547615[19] = 1.0;
   out_6557368431862547615[20] = 0.0;
   out_6557368431862547615[21] = 0.0;
   out_6557368431862547615[22] = 0.0;
   out_6557368431862547615[23] = 0.0;
   out_6557368431862547615[24] = 0.0;
   out_6557368431862547615[25] = 0.0;
   out_6557368431862547615[26] = 0.0;
   out_6557368431862547615[27] = 0.0;
   out_6557368431862547615[28] = 0.0;
   out_6557368431862547615[29] = 0.0;
   out_6557368431862547615[30] = 0.0;
   out_6557368431862547615[31] = 0.0;
   out_6557368431862547615[32] = 0.0;
   out_6557368431862547615[33] = 0.0;
   out_6557368431862547615[34] = 0.0;
   out_6557368431862547615[35] = 0.0;
   out_6557368431862547615[36] = 0.0;
   out_6557368431862547615[37] = 0.0;
   out_6557368431862547615[38] = 1.0;
   out_6557368431862547615[39] = 0.0;
   out_6557368431862547615[40] = 0.0;
   out_6557368431862547615[41] = 0.0;
   out_6557368431862547615[42] = 0.0;
   out_6557368431862547615[43] = 0.0;
   out_6557368431862547615[44] = 0.0;
   out_6557368431862547615[45] = 0.0;
   out_6557368431862547615[46] = 0.0;
   out_6557368431862547615[47] = 0.0;
   out_6557368431862547615[48] = 0.0;
   out_6557368431862547615[49] = 0.0;
   out_6557368431862547615[50] = 0.0;
   out_6557368431862547615[51] = 0.0;
   out_6557368431862547615[52] = 0.0;
   out_6557368431862547615[53] = 0.0;
   out_6557368431862547615[54] = 0.0;
   out_6557368431862547615[55] = 0.0;
   out_6557368431862547615[56] = 0.0;
   out_6557368431862547615[57] = 1.0;
   out_6557368431862547615[58] = 0.0;
   out_6557368431862547615[59] = 0.0;
   out_6557368431862547615[60] = 0.0;
   out_6557368431862547615[61] = 0.0;
   out_6557368431862547615[62] = 0.0;
   out_6557368431862547615[63] = 0.0;
   out_6557368431862547615[64] = 0.0;
   out_6557368431862547615[65] = 0.0;
   out_6557368431862547615[66] = 0.0;
   out_6557368431862547615[67] = 0.0;
   out_6557368431862547615[68] = 0.0;
   out_6557368431862547615[69] = 0.0;
   out_6557368431862547615[70] = 0.0;
   out_6557368431862547615[71] = 0.0;
   out_6557368431862547615[72] = 0.0;
   out_6557368431862547615[73] = 0.0;
   out_6557368431862547615[74] = 0.0;
   out_6557368431862547615[75] = 0.0;
   out_6557368431862547615[76] = 1.0;
   out_6557368431862547615[77] = 0.0;
   out_6557368431862547615[78] = 0.0;
   out_6557368431862547615[79] = 0.0;
   out_6557368431862547615[80] = 0.0;
   out_6557368431862547615[81] = 0.0;
   out_6557368431862547615[82] = 0.0;
   out_6557368431862547615[83] = 0.0;
   out_6557368431862547615[84] = 0.0;
   out_6557368431862547615[85] = 0.0;
   out_6557368431862547615[86] = 0.0;
   out_6557368431862547615[87] = 0.0;
   out_6557368431862547615[88] = 0.0;
   out_6557368431862547615[89] = 0.0;
   out_6557368431862547615[90] = 0.0;
   out_6557368431862547615[91] = 0.0;
   out_6557368431862547615[92] = 0.0;
   out_6557368431862547615[93] = 0.0;
   out_6557368431862547615[94] = 0.0;
   out_6557368431862547615[95] = 1.0;
   out_6557368431862547615[96] = 0.0;
   out_6557368431862547615[97] = 0.0;
   out_6557368431862547615[98] = 0.0;
   out_6557368431862547615[99] = 0.0;
   out_6557368431862547615[100] = 0.0;
   out_6557368431862547615[101] = 0.0;
   out_6557368431862547615[102] = 0.0;
   out_6557368431862547615[103] = 0.0;
   out_6557368431862547615[104] = 0.0;
   out_6557368431862547615[105] = 0.0;
   out_6557368431862547615[106] = 0.0;
   out_6557368431862547615[107] = 0.0;
   out_6557368431862547615[108] = 0.0;
   out_6557368431862547615[109] = 0.0;
   out_6557368431862547615[110] = 0.0;
   out_6557368431862547615[111] = 0.0;
   out_6557368431862547615[112] = 0.0;
   out_6557368431862547615[113] = 0.0;
   out_6557368431862547615[114] = 1.0;
   out_6557368431862547615[115] = 0.0;
   out_6557368431862547615[116] = 0.0;
   out_6557368431862547615[117] = 0.0;
   out_6557368431862547615[118] = 0.0;
   out_6557368431862547615[119] = 0.0;
   out_6557368431862547615[120] = 0.0;
   out_6557368431862547615[121] = 0.0;
   out_6557368431862547615[122] = 0.0;
   out_6557368431862547615[123] = 0.0;
   out_6557368431862547615[124] = 0.0;
   out_6557368431862547615[125] = 0.0;
   out_6557368431862547615[126] = 0.0;
   out_6557368431862547615[127] = 0.0;
   out_6557368431862547615[128] = 0.0;
   out_6557368431862547615[129] = 0.0;
   out_6557368431862547615[130] = 0.0;
   out_6557368431862547615[131] = 0.0;
   out_6557368431862547615[132] = 0.0;
   out_6557368431862547615[133] = 1.0;
   out_6557368431862547615[134] = 0.0;
   out_6557368431862547615[135] = 0.0;
   out_6557368431862547615[136] = 0.0;
   out_6557368431862547615[137] = 0.0;
   out_6557368431862547615[138] = 0.0;
   out_6557368431862547615[139] = 0.0;
   out_6557368431862547615[140] = 0.0;
   out_6557368431862547615[141] = 0.0;
   out_6557368431862547615[142] = 0.0;
   out_6557368431862547615[143] = 0.0;
   out_6557368431862547615[144] = 0.0;
   out_6557368431862547615[145] = 0.0;
   out_6557368431862547615[146] = 0.0;
   out_6557368431862547615[147] = 0.0;
   out_6557368431862547615[148] = 0.0;
   out_6557368431862547615[149] = 0.0;
   out_6557368431862547615[150] = 0.0;
   out_6557368431862547615[151] = 0.0;
   out_6557368431862547615[152] = 1.0;
   out_6557368431862547615[153] = 0.0;
   out_6557368431862547615[154] = 0.0;
   out_6557368431862547615[155] = 0.0;
   out_6557368431862547615[156] = 0.0;
   out_6557368431862547615[157] = 0.0;
   out_6557368431862547615[158] = 0.0;
   out_6557368431862547615[159] = 0.0;
   out_6557368431862547615[160] = 0.0;
   out_6557368431862547615[161] = 0.0;
   out_6557368431862547615[162] = 0.0;
   out_6557368431862547615[163] = 0.0;
   out_6557368431862547615[164] = 0.0;
   out_6557368431862547615[165] = 0.0;
   out_6557368431862547615[166] = 0.0;
   out_6557368431862547615[167] = 0.0;
   out_6557368431862547615[168] = 0.0;
   out_6557368431862547615[169] = 0.0;
   out_6557368431862547615[170] = 0.0;
   out_6557368431862547615[171] = 1.0;
   out_6557368431862547615[172] = 0.0;
   out_6557368431862547615[173] = 0.0;
   out_6557368431862547615[174] = 0.0;
   out_6557368431862547615[175] = 0.0;
   out_6557368431862547615[176] = 0.0;
   out_6557368431862547615[177] = 0.0;
   out_6557368431862547615[178] = 0.0;
   out_6557368431862547615[179] = 0.0;
   out_6557368431862547615[180] = 0.0;
   out_6557368431862547615[181] = 0.0;
   out_6557368431862547615[182] = 0.0;
   out_6557368431862547615[183] = 0.0;
   out_6557368431862547615[184] = 0.0;
   out_6557368431862547615[185] = 0.0;
   out_6557368431862547615[186] = 0.0;
   out_6557368431862547615[187] = 0.0;
   out_6557368431862547615[188] = 0.0;
   out_6557368431862547615[189] = 0.0;
   out_6557368431862547615[190] = 1.0;
   out_6557368431862547615[191] = 0.0;
   out_6557368431862547615[192] = 0.0;
   out_6557368431862547615[193] = 0.0;
   out_6557368431862547615[194] = 0.0;
   out_6557368431862547615[195] = 0.0;
   out_6557368431862547615[196] = 0.0;
   out_6557368431862547615[197] = 0.0;
   out_6557368431862547615[198] = 0.0;
   out_6557368431862547615[199] = 0.0;
   out_6557368431862547615[200] = 0.0;
   out_6557368431862547615[201] = 0.0;
   out_6557368431862547615[202] = 0.0;
   out_6557368431862547615[203] = 0.0;
   out_6557368431862547615[204] = 0.0;
   out_6557368431862547615[205] = 0.0;
   out_6557368431862547615[206] = 0.0;
   out_6557368431862547615[207] = 0.0;
   out_6557368431862547615[208] = 0.0;
   out_6557368431862547615[209] = 1.0;
   out_6557368431862547615[210] = 0.0;
   out_6557368431862547615[211] = 0.0;
   out_6557368431862547615[212] = 0.0;
   out_6557368431862547615[213] = 0.0;
   out_6557368431862547615[214] = 0.0;
   out_6557368431862547615[215] = 0.0;
   out_6557368431862547615[216] = 0.0;
   out_6557368431862547615[217] = 0.0;
   out_6557368431862547615[218] = 0.0;
   out_6557368431862547615[219] = 0.0;
   out_6557368431862547615[220] = 0.0;
   out_6557368431862547615[221] = 0.0;
   out_6557368431862547615[222] = 0.0;
   out_6557368431862547615[223] = 0.0;
   out_6557368431862547615[224] = 0.0;
   out_6557368431862547615[225] = 0.0;
   out_6557368431862547615[226] = 0.0;
   out_6557368431862547615[227] = 0.0;
   out_6557368431862547615[228] = 1.0;
   out_6557368431862547615[229] = 0.0;
   out_6557368431862547615[230] = 0.0;
   out_6557368431862547615[231] = 0.0;
   out_6557368431862547615[232] = 0.0;
   out_6557368431862547615[233] = 0.0;
   out_6557368431862547615[234] = 0.0;
   out_6557368431862547615[235] = 0.0;
   out_6557368431862547615[236] = 0.0;
   out_6557368431862547615[237] = 0.0;
   out_6557368431862547615[238] = 0.0;
   out_6557368431862547615[239] = 0.0;
   out_6557368431862547615[240] = 0.0;
   out_6557368431862547615[241] = 0.0;
   out_6557368431862547615[242] = 0.0;
   out_6557368431862547615[243] = 0.0;
   out_6557368431862547615[244] = 0.0;
   out_6557368431862547615[245] = 0.0;
   out_6557368431862547615[246] = 0.0;
   out_6557368431862547615[247] = 1.0;
   out_6557368431862547615[248] = 0.0;
   out_6557368431862547615[249] = 0.0;
   out_6557368431862547615[250] = 0.0;
   out_6557368431862547615[251] = 0.0;
   out_6557368431862547615[252] = 0.0;
   out_6557368431862547615[253] = 0.0;
   out_6557368431862547615[254] = 0.0;
   out_6557368431862547615[255] = 0.0;
   out_6557368431862547615[256] = 0.0;
   out_6557368431862547615[257] = 0.0;
   out_6557368431862547615[258] = 0.0;
   out_6557368431862547615[259] = 0.0;
   out_6557368431862547615[260] = 0.0;
   out_6557368431862547615[261] = 0.0;
   out_6557368431862547615[262] = 0.0;
   out_6557368431862547615[263] = 0.0;
   out_6557368431862547615[264] = 0.0;
   out_6557368431862547615[265] = 0.0;
   out_6557368431862547615[266] = 1.0;
   out_6557368431862547615[267] = 0.0;
   out_6557368431862547615[268] = 0.0;
   out_6557368431862547615[269] = 0.0;
   out_6557368431862547615[270] = 0.0;
   out_6557368431862547615[271] = 0.0;
   out_6557368431862547615[272] = 0.0;
   out_6557368431862547615[273] = 0.0;
   out_6557368431862547615[274] = 0.0;
   out_6557368431862547615[275] = 0.0;
   out_6557368431862547615[276] = 0.0;
   out_6557368431862547615[277] = 0.0;
   out_6557368431862547615[278] = 0.0;
   out_6557368431862547615[279] = 0.0;
   out_6557368431862547615[280] = 0.0;
   out_6557368431862547615[281] = 0.0;
   out_6557368431862547615[282] = 0.0;
   out_6557368431862547615[283] = 0.0;
   out_6557368431862547615[284] = 0.0;
   out_6557368431862547615[285] = 1.0;
   out_6557368431862547615[286] = 0.0;
   out_6557368431862547615[287] = 0.0;
   out_6557368431862547615[288] = 0.0;
   out_6557368431862547615[289] = 0.0;
   out_6557368431862547615[290] = 0.0;
   out_6557368431862547615[291] = 0.0;
   out_6557368431862547615[292] = 0.0;
   out_6557368431862547615[293] = 0.0;
   out_6557368431862547615[294] = 0.0;
   out_6557368431862547615[295] = 0.0;
   out_6557368431862547615[296] = 0.0;
   out_6557368431862547615[297] = 0.0;
   out_6557368431862547615[298] = 0.0;
   out_6557368431862547615[299] = 0.0;
   out_6557368431862547615[300] = 0.0;
   out_6557368431862547615[301] = 0.0;
   out_6557368431862547615[302] = 0.0;
   out_6557368431862547615[303] = 0.0;
   out_6557368431862547615[304] = 1.0;
   out_6557368431862547615[305] = 0.0;
   out_6557368431862547615[306] = 0.0;
   out_6557368431862547615[307] = 0.0;
   out_6557368431862547615[308] = 0.0;
   out_6557368431862547615[309] = 0.0;
   out_6557368431862547615[310] = 0.0;
   out_6557368431862547615[311] = 0.0;
   out_6557368431862547615[312] = 0.0;
   out_6557368431862547615[313] = 0.0;
   out_6557368431862547615[314] = 0.0;
   out_6557368431862547615[315] = 0.0;
   out_6557368431862547615[316] = 0.0;
   out_6557368431862547615[317] = 0.0;
   out_6557368431862547615[318] = 0.0;
   out_6557368431862547615[319] = 0.0;
   out_6557368431862547615[320] = 0.0;
   out_6557368431862547615[321] = 0.0;
   out_6557368431862547615[322] = 0.0;
   out_6557368431862547615[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8766002253507214463) {
   out_8766002253507214463[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8766002253507214463[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8766002253507214463[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8766002253507214463[3] = dt*state[12] + state[3];
   out_8766002253507214463[4] = dt*state[13] + state[4];
   out_8766002253507214463[5] = dt*state[14] + state[5];
   out_8766002253507214463[6] = state[6];
   out_8766002253507214463[7] = state[7];
   out_8766002253507214463[8] = state[8];
   out_8766002253507214463[9] = state[9];
   out_8766002253507214463[10] = state[10];
   out_8766002253507214463[11] = state[11];
   out_8766002253507214463[12] = state[12];
   out_8766002253507214463[13] = state[13];
   out_8766002253507214463[14] = state[14];
   out_8766002253507214463[15] = state[15];
   out_8766002253507214463[16] = state[16];
   out_8766002253507214463[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7027423975176096545) {
   out_7027423975176096545[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7027423975176096545[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7027423975176096545[2] = 0;
   out_7027423975176096545[3] = 0;
   out_7027423975176096545[4] = 0;
   out_7027423975176096545[5] = 0;
   out_7027423975176096545[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7027423975176096545[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7027423975176096545[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7027423975176096545[9] = 0;
   out_7027423975176096545[10] = 0;
   out_7027423975176096545[11] = 0;
   out_7027423975176096545[12] = 0;
   out_7027423975176096545[13] = 0;
   out_7027423975176096545[14] = 0;
   out_7027423975176096545[15] = 0;
   out_7027423975176096545[16] = 0;
   out_7027423975176096545[17] = 0;
   out_7027423975176096545[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7027423975176096545[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7027423975176096545[20] = 0;
   out_7027423975176096545[21] = 0;
   out_7027423975176096545[22] = 0;
   out_7027423975176096545[23] = 0;
   out_7027423975176096545[24] = 0;
   out_7027423975176096545[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7027423975176096545[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7027423975176096545[27] = 0;
   out_7027423975176096545[28] = 0;
   out_7027423975176096545[29] = 0;
   out_7027423975176096545[30] = 0;
   out_7027423975176096545[31] = 0;
   out_7027423975176096545[32] = 0;
   out_7027423975176096545[33] = 0;
   out_7027423975176096545[34] = 0;
   out_7027423975176096545[35] = 0;
   out_7027423975176096545[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7027423975176096545[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7027423975176096545[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7027423975176096545[39] = 0;
   out_7027423975176096545[40] = 0;
   out_7027423975176096545[41] = 0;
   out_7027423975176096545[42] = 0;
   out_7027423975176096545[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7027423975176096545[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7027423975176096545[45] = 0;
   out_7027423975176096545[46] = 0;
   out_7027423975176096545[47] = 0;
   out_7027423975176096545[48] = 0;
   out_7027423975176096545[49] = 0;
   out_7027423975176096545[50] = 0;
   out_7027423975176096545[51] = 0;
   out_7027423975176096545[52] = 0;
   out_7027423975176096545[53] = 0;
   out_7027423975176096545[54] = 0;
   out_7027423975176096545[55] = 0;
   out_7027423975176096545[56] = 0;
   out_7027423975176096545[57] = 1;
   out_7027423975176096545[58] = 0;
   out_7027423975176096545[59] = 0;
   out_7027423975176096545[60] = 0;
   out_7027423975176096545[61] = 0;
   out_7027423975176096545[62] = 0;
   out_7027423975176096545[63] = 0;
   out_7027423975176096545[64] = 0;
   out_7027423975176096545[65] = 0;
   out_7027423975176096545[66] = dt;
   out_7027423975176096545[67] = 0;
   out_7027423975176096545[68] = 0;
   out_7027423975176096545[69] = 0;
   out_7027423975176096545[70] = 0;
   out_7027423975176096545[71] = 0;
   out_7027423975176096545[72] = 0;
   out_7027423975176096545[73] = 0;
   out_7027423975176096545[74] = 0;
   out_7027423975176096545[75] = 0;
   out_7027423975176096545[76] = 1;
   out_7027423975176096545[77] = 0;
   out_7027423975176096545[78] = 0;
   out_7027423975176096545[79] = 0;
   out_7027423975176096545[80] = 0;
   out_7027423975176096545[81] = 0;
   out_7027423975176096545[82] = 0;
   out_7027423975176096545[83] = 0;
   out_7027423975176096545[84] = 0;
   out_7027423975176096545[85] = dt;
   out_7027423975176096545[86] = 0;
   out_7027423975176096545[87] = 0;
   out_7027423975176096545[88] = 0;
   out_7027423975176096545[89] = 0;
   out_7027423975176096545[90] = 0;
   out_7027423975176096545[91] = 0;
   out_7027423975176096545[92] = 0;
   out_7027423975176096545[93] = 0;
   out_7027423975176096545[94] = 0;
   out_7027423975176096545[95] = 1;
   out_7027423975176096545[96] = 0;
   out_7027423975176096545[97] = 0;
   out_7027423975176096545[98] = 0;
   out_7027423975176096545[99] = 0;
   out_7027423975176096545[100] = 0;
   out_7027423975176096545[101] = 0;
   out_7027423975176096545[102] = 0;
   out_7027423975176096545[103] = 0;
   out_7027423975176096545[104] = dt;
   out_7027423975176096545[105] = 0;
   out_7027423975176096545[106] = 0;
   out_7027423975176096545[107] = 0;
   out_7027423975176096545[108] = 0;
   out_7027423975176096545[109] = 0;
   out_7027423975176096545[110] = 0;
   out_7027423975176096545[111] = 0;
   out_7027423975176096545[112] = 0;
   out_7027423975176096545[113] = 0;
   out_7027423975176096545[114] = 1;
   out_7027423975176096545[115] = 0;
   out_7027423975176096545[116] = 0;
   out_7027423975176096545[117] = 0;
   out_7027423975176096545[118] = 0;
   out_7027423975176096545[119] = 0;
   out_7027423975176096545[120] = 0;
   out_7027423975176096545[121] = 0;
   out_7027423975176096545[122] = 0;
   out_7027423975176096545[123] = 0;
   out_7027423975176096545[124] = 0;
   out_7027423975176096545[125] = 0;
   out_7027423975176096545[126] = 0;
   out_7027423975176096545[127] = 0;
   out_7027423975176096545[128] = 0;
   out_7027423975176096545[129] = 0;
   out_7027423975176096545[130] = 0;
   out_7027423975176096545[131] = 0;
   out_7027423975176096545[132] = 0;
   out_7027423975176096545[133] = 1;
   out_7027423975176096545[134] = 0;
   out_7027423975176096545[135] = 0;
   out_7027423975176096545[136] = 0;
   out_7027423975176096545[137] = 0;
   out_7027423975176096545[138] = 0;
   out_7027423975176096545[139] = 0;
   out_7027423975176096545[140] = 0;
   out_7027423975176096545[141] = 0;
   out_7027423975176096545[142] = 0;
   out_7027423975176096545[143] = 0;
   out_7027423975176096545[144] = 0;
   out_7027423975176096545[145] = 0;
   out_7027423975176096545[146] = 0;
   out_7027423975176096545[147] = 0;
   out_7027423975176096545[148] = 0;
   out_7027423975176096545[149] = 0;
   out_7027423975176096545[150] = 0;
   out_7027423975176096545[151] = 0;
   out_7027423975176096545[152] = 1;
   out_7027423975176096545[153] = 0;
   out_7027423975176096545[154] = 0;
   out_7027423975176096545[155] = 0;
   out_7027423975176096545[156] = 0;
   out_7027423975176096545[157] = 0;
   out_7027423975176096545[158] = 0;
   out_7027423975176096545[159] = 0;
   out_7027423975176096545[160] = 0;
   out_7027423975176096545[161] = 0;
   out_7027423975176096545[162] = 0;
   out_7027423975176096545[163] = 0;
   out_7027423975176096545[164] = 0;
   out_7027423975176096545[165] = 0;
   out_7027423975176096545[166] = 0;
   out_7027423975176096545[167] = 0;
   out_7027423975176096545[168] = 0;
   out_7027423975176096545[169] = 0;
   out_7027423975176096545[170] = 0;
   out_7027423975176096545[171] = 1;
   out_7027423975176096545[172] = 0;
   out_7027423975176096545[173] = 0;
   out_7027423975176096545[174] = 0;
   out_7027423975176096545[175] = 0;
   out_7027423975176096545[176] = 0;
   out_7027423975176096545[177] = 0;
   out_7027423975176096545[178] = 0;
   out_7027423975176096545[179] = 0;
   out_7027423975176096545[180] = 0;
   out_7027423975176096545[181] = 0;
   out_7027423975176096545[182] = 0;
   out_7027423975176096545[183] = 0;
   out_7027423975176096545[184] = 0;
   out_7027423975176096545[185] = 0;
   out_7027423975176096545[186] = 0;
   out_7027423975176096545[187] = 0;
   out_7027423975176096545[188] = 0;
   out_7027423975176096545[189] = 0;
   out_7027423975176096545[190] = 1;
   out_7027423975176096545[191] = 0;
   out_7027423975176096545[192] = 0;
   out_7027423975176096545[193] = 0;
   out_7027423975176096545[194] = 0;
   out_7027423975176096545[195] = 0;
   out_7027423975176096545[196] = 0;
   out_7027423975176096545[197] = 0;
   out_7027423975176096545[198] = 0;
   out_7027423975176096545[199] = 0;
   out_7027423975176096545[200] = 0;
   out_7027423975176096545[201] = 0;
   out_7027423975176096545[202] = 0;
   out_7027423975176096545[203] = 0;
   out_7027423975176096545[204] = 0;
   out_7027423975176096545[205] = 0;
   out_7027423975176096545[206] = 0;
   out_7027423975176096545[207] = 0;
   out_7027423975176096545[208] = 0;
   out_7027423975176096545[209] = 1;
   out_7027423975176096545[210] = 0;
   out_7027423975176096545[211] = 0;
   out_7027423975176096545[212] = 0;
   out_7027423975176096545[213] = 0;
   out_7027423975176096545[214] = 0;
   out_7027423975176096545[215] = 0;
   out_7027423975176096545[216] = 0;
   out_7027423975176096545[217] = 0;
   out_7027423975176096545[218] = 0;
   out_7027423975176096545[219] = 0;
   out_7027423975176096545[220] = 0;
   out_7027423975176096545[221] = 0;
   out_7027423975176096545[222] = 0;
   out_7027423975176096545[223] = 0;
   out_7027423975176096545[224] = 0;
   out_7027423975176096545[225] = 0;
   out_7027423975176096545[226] = 0;
   out_7027423975176096545[227] = 0;
   out_7027423975176096545[228] = 1;
   out_7027423975176096545[229] = 0;
   out_7027423975176096545[230] = 0;
   out_7027423975176096545[231] = 0;
   out_7027423975176096545[232] = 0;
   out_7027423975176096545[233] = 0;
   out_7027423975176096545[234] = 0;
   out_7027423975176096545[235] = 0;
   out_7027423975176096545[236] = 0;
   out_7027423975176096545[237] = 0;
   out_7027423975176096545[238] = 0;
   out_7027423975176096545[239] = 0;
   out_7027423975176096545[240] = 0;
   out_7027423975176096545[241] = 0;
   out_7027423975176096545[242] = 0;
   out_7027423975176096545[243] = 0;
   out_7027423975176096545[244] = 0;
   out_7027423975176096545[245] = 0;
   out_7027423975176096545[246] = 0;
   out_7027423975176096545[247] = 1;
   out_7027423975176096545[248] = 0;
   out_7027423975176096545[249] = 0;
   out_7027423975176096545[250] = 0;
   out_7027423975176096545[251] = 0;
   out_7027423975176096545[252] = 0;
   out_7027423975176096545[253] = 0;
   out_7027423975176096545[254] = 0;
   out_7027423975176096545[255] = 0;
   out_7027423975176096545[256] = 0;
   out_7027423975176096545[257] = 0;
   out_7027423975176096545[258] = 0;
   out_7027423975176096545[259] = 0;
   out_7027423975176096545[260] = 0;
   out_7027423975176096545[261] = 0;
   out_7027423975176096545[262] = 0;
   out_7027423975176096545[263] = 0;
   out_7027423975176096545[264] = 0;
   out_7027423975176096545[265] = 0;
   out_7027423975176096545[266] = 1;
   out_7027423975176096545[267] = 0;
   out_7027423975176096545[268] = 0;
   out_7027423975176096545[269] = 0;
   out_7027423975176096545[270] = 0;
   out_7027423975176096545[271] = 0;
   out_7027423975176096545[272] = 0;
   out_7027423975176096545[273] = 0;
   out_7027423975176096545[274] = 0;
   out_7027423975176096545[275] = 0;
   out_7027423975176096545[276] = 0;
   out_7027423975176096545[277] = 0;
   out_7027423975176096545[278] = 0;
   out_7027423975176096545[279] = 0;
   out_7027423975176096545[280] = 0;
   out_7027423975176096545[281] = 0;
   out_7027423975176096545[282] = 0;
   out_7027423975176096545[283] = 0;
   out_7027423975176096545[284] = 0;
   out_7027423975176096545[285] = 1;
   out_7027423975176096545[286] = 0;
   out_7027423975176096545[287] = 0;
   out_7027423975176096545[288] = 0;
   out_7027423975176096545[289] = 0;
   out_7027423975176096545[290] = 0;
   out_7027423975176096545[291] = 0;
   out_7027423975176096545[292] = 0;
   out_7027423975176096545[293] = 0;
   out_7027423975176096545[294] = 0;
   out_7027423975176096545[295] = 0;
   out_7027423975176096545[296] = 0;
   out_7027423975176096545[297] = 0;
   out_7027423975176096545[298] = 0;
   out_7027423975176096545[299] = 0;
   out_7027423975176096545[300] = 0;
   out_7027423975176096545[301] = 0;
   out_7027423975176096545[302] = 0;
   out_7027423975176096545[303] = 0;
   out_7027423975176096545[304] = 1;
   out_7027423975176096545[305] = 0;
   out_7027423975176096545[306] = 0;
   out_7027423975176096545[307] = 0;
   out_7027423975176096545[308] = 0;
   out_7027423975176096545[309] = 0;
   out_7027423975176096545[310] = 0;
   out_7027423975176096545[311] = 0;
   out_7027423975176096545[312] = 0;
   out_7027423975176096545[313] = 0;
   out_7027423975176096545[314] = 0;
   out_7027423975176096545[315] = 0;
   out_7027423975176096545[316] = 0;
   out_7027423975176096545[317] = 0;
   out_7027423975176096545[318] = 0;
   out_7027423975176096545[319] = 0;
   out_7027423975176096545[320] = 0;
   out_7027423975176096545[321] = 0;
   out_7027423975176096545[322] = 0;
   out_7027423975176096545[323] = 1;
}
void h_4(double *state, double *unused, double *out_8406635548758778985) {
   out_8406635548758778985[0] = state[6] + state[9];
   out_8406635548758778985[1] = state[7] + state[10];
   out_8406635548758778985[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_9087533728568900293) {
   out_9087533728568900293[0] = 0;
   out_9087533728568900293[1] = 0;
   out_9087533728568900293[2] = 0;
   out_9087533728568900293[3] = 0;
   out_9087533728568900293[4] = 0;
   out_9087533728568900293[5] = 0;
   out_9087533728568900293[6] = 1;
   out_9087533728568900293[7] = 0;
   out_9087533728568900293[8] = 0;
   out_9087533728568900293[9] = 1;
   out_9087533728568900293[10] = 0;
   out_9087533728568900293[11] = 0;
   out_9087533728568900293[12] = 0;
   out_9087533728568900293[13] = 0;
   out_9087533728568900293[14] = 0;
   out_9087533728568900293[15] = 0;
   out_9087533728568900293[16] = 0;
   out_9087533728568900293[17] = 0;
   out_9087533728568900293[18] = 0;
   out_9087533728568900293[19] = 0;
   out_9087533728568900293[20] = 0;
   out_9087533728568900293[21] = 0;
   out_9087533728568900293[22] = 0;
   out_9087533728568900293[23] = 0;
   out_9087533728568900293[24] = 0;
   out_9087533728568900293[25] = 1;
   out_9087533728568900293[26] = 0;
   out_9087533728568900293[27] = 0;
   out_9087533728568900293[28] = 1;
   out_9087533728568900293[29] = 0;
   out_9087533728568900293[30] = 0;
   out_9087533728568900293[31] = 0;
   out_9087533728568900293[32] = 0;
   out_9087533728568900293[33] = 0;
   out_9087533728568900293[34] = 0;
   out_9087533728568900293[35] = 0;
   out_9087533728568900293[36] = 0;
   out_9087533728568900293[37] = 0;
   out_9087533728568900293[38] = 0;
   out_9087533728568900293[39] = 0;
   out_9087533728568900293[40] = 0;
   out_9087533728568900293[41] = 0;
   out_9087533728568900293[42] = 0;
   out_9087533728568900293[43] = 0;
   out_9087533728568900293[44] = 1;
   out_9087533728568900293[45] = 0;
   out_9087533728568900293[46] = 0;
   out_9087533728568900293[47] = 1;
   out_9087533728568900293[48] = 0;
   out_9087533728568900293[49] = 0;
   out_9087533728568900293[50] = 0;
   out_9087533728568900293[51] = 0;
   out_9087533728568900293[52] = 0;
   out_9087533728568900293[53] = 0;
}
void h_10(double *state, double *unused, double *out_4724563756245089329) {
   out_4724563756245089329[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4724563756245089329[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4724563756245089329[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_151772769759508374) {
   out_151772769759508374[0] = 0;
   out_151772769759508374[1] = 9.8100000000000005*cos(state[1]);
   out_151772769759508374[2] = 0;
   out_151772769759508374[3] = 0;
   out_151772769759508374[4] = -state[8];
   out_151772769759508374[5] = state[7];
   out_151772769759508374[6] = 0;
   out_151772769759508374[7] = state[5];
   out_151772769759508374[8] = -state[4];
   out_151772769759508374[9] = 0;
   out_151772769759508374[10] = 0;
   out_151772769759508374[11] = 0;
   out_151772769759508374[12] = 1;
   out_151772769759508374[13] = 0;
   out_151772769759508374[14] = 0;
   out_151772769759508374[15] = 1;
   out_151772769759508374[16] = 0;
   out_151772769759508374[17] = 0;
   out_151772769759508374[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_151772769759508374[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_151772769759508374[20] = 0;
   out_151772769759508374[21] = state[8];
   out_151772769759508374[22] = 0;
   out_151772769759508374[23] = -state[6];
   out_151772769759508374[24] = -state[5];
   out_151772769759508374[25] = 0;
   out_151772769759508374[26] = state[3];
   out_151772769759508374[27] = 0;
   out_151772769759508374[28] = 0;
   out_151772769759508374[29] = 0;
   out_151772769759508374[30] = 0;
   out_151772769759508374[31] = 1;
   out_151772769759508374[32] = 0;
   out_151772769759508374[33] = 0;
   out_151772769759508374[34] = 1;
   out_151772769759508374[35] = 0;
   out_151772769759508374[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_151772769759508374[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_151772769759508374[38] = 0;
   out_151772769759508374[39] = -state[7];
   out_151772769759508374[40] = state[6];
   out_151772769759508374[41] = 0;
   out_151772769759508374[42] = state[4];
   out_151772769759508374[43] = -state[3];
   out_151772769759508374[44] = 0;
   out_151772769759508374[45] = 0;
   out_151772769759508374[46] = 0;
   out_151772769759508374[47] = 0;
   out_151772769759508374[48] = 0;
   out_151772769759508374[49] = 0;
   out_151772769759508374[50] = 1;
   out_151772769759508374[51] = 0;
   out_151772769759508374[52] = 0;
   out_151772769759508374[53] = 1;
}
void h_13(double *state, double *unused, double *out_916448766757343904) {
   out_916448766757343904[0] = state[3];
   out_916448766757343904[1] = state[4];
   out_916448766757343904[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1748579136823950394) {
   out_1748579136823950394[0] = 0;
   out_1748579136823950394[1] = 0;
   out_1748579136823950394[2] = 0;
   out_1748579136823950394[3] = 1;
   out_1748579136823950394[4] = 0;
   out_1748579136823950394[5] = 0;
   out_1748579136823950394[6] = 0;
   out_1748579136823950394[7] = 0;
   out_1748579136823950394[8] = 0;
   out_1748579136823950394[9] = 0;
   out_1748579136823950394[10] = 0;
   out_1748579136823950394[11] = 0;
   out_1748579136823950394[12] = 0;
   out_1748579136823950394[13] = 0;
   out_1748579136823950394[14] = 0;
   out_1748579136823950394[15] = 0;
   out_1748579136823950394[16] = 0;
   out_1748579136823950394[17] = 0;
   out_1748579136823950394[18] = 0;
   out_1748579136823950394[19] = 0;
   out_1748579136823950394[20] = 0;
   out_1748579136823950394[21] = 0;
   out_1748579136823950394[22] = 1;
   out_1748579136823950394[23] = 0;
   out_1748579136823950394[24] = 0;
   out_1748579136823950394[25] = 0;
   out_1748579136823950394[26] = 0;
   out_1748579136823950394[27] = 0;
   out_1748579136823950394[28] = 0;
   out_1748579136823950394[29] = 0;
   out_1748579136823950394[30] = 0;
   out_1748579136823950394[31] = 0;
   out_1748579136823950394[32] = 0;
   out_1748579136823950394[33] = 0;
   out_1748579136823950394[34] = 0;
   out_1748579136823950394[35] = 0;
   out_1748579136823950394[36] = 0;
   out_1748579136823950394[37] = 0;
   out_1748579136823950394[38] = 0;
   out_1748579136823950394[39] = 0;
   out_1748579136823950394[40] = 0;
   out_1748579136823950394[41] = 1;
   out_1748579136823950394[42] = 0;
   out_1748579136823950394[43] = 0;
   out_1748579136823950394[44] = 0;
   out_1748579136823950394[45] = 0;
   out_1748579136823950394[46] = 0;
   out_1748579136823950394[47] = 0;
   out_1748579136823950394[48] = 0;
   out_1748579136823950394[49] = 0;
   out_1748579136823950394[50] = 0;
   out_1748579136823950394[51] = 0;
   out_1748579136823950394[52] = 0;
   out_1748579136823950394[53] = 0;
}
void h_14(double *state, double *unused, double *out_4320749477702954633) {
   out_4320749477702954633[0] = state[6];
   out_4320749477702954633[1] = state[7];
   out_4320749477702954633[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6004745296273527997) {
   out_6004745296273527997[0] = 0;
   out_6004745296273527997[1] = 0;
   out_6004745296273527997[2] = 0;
   out_6004745296273527997[3] = 0;
   out_6004745296273527997[4] = 0;
   out_6004745296273527997[5] = 0;
   out_6004745296273527997[6] = 1;
   out_6004745296273527997[7] = 0;
   out_6004745296273527997[8] = 0;
   out_6004745296273527997[9] = 0;
   out_6004745296273527997[10] = 0;
   out_6004745296273527997[11] = 0;
   out_6004745296273527997[12] = 0;
   out_6004745296273527997[13] = 0;
   out_6004745296273527997[14] = 0;
   out_6004745296273527997[15] = 0;
   out_6004745296273527997[16] = 0;
   out_6004745296273527997[17] = 0;
   out_6004745296273527997[18] = 0;
   out_6004745296273527997[19] = 0;
   out_6004745296273527997[20] = 0;
   out_6004745296273527997[21] = 0;
   out_6004745296273527997[22] = 0;
   out_6004745296273527997[23] = 0;
   out_6004745296273527997[24] = 0;
   out_6004745296273527997[25] = 1;
   out_6004745296273527997[26] = 0;
   out_6004745296273527997[27] = 0;
   out_6004745296273527997[28] = 0;
   out_6004745296273527997[29] = 0;
   out_6004745296273527997[30] = 0;
   out_6004745296273527997[31] = 0;
   out_6004745296273527997[32] = 0;
   out_6004745296273527997[33] = 0;
   out_6004745296273527997[34] = 0;
   out_6004745296273527997[35] = 0;
   out_6004745296273527997[36] = 0;
   out_6004745296273527997[37] = 0;
   out_6004745296273527997[38] = 0;
   out_6004745296273527997[39] = 0;
   out_6004745296273527997[40] = 0;
   out_6004745296273527997[41] = 0;
   out_6004745296273527997[42] = 0;
   out_6004745296273527997[43] = 0;
   out_6004745296273527997[44] = 1;
   out_6004745296273527997[45] = 0;
   out_6004745296273527997[46] = 0;
   out_6004745296273527997[47] = 0;
   out_6004745296273527997[48] = 0;
   out_6004745296273527997[49] = 0;
   out_6004745296273527997[50] = 0;
   out_6004745296273527997[51] = 0;
   out_6004745296273527997[52] = 0;
   out_6004745296273527997[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_1366452659282605760) {
  err_fun(nom_x, delta_x, out_1366452659282605760);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_633665134700440095) {
  inv_err_fun(nom_x, true_x, out_633665134700440095);
}
void pose_H_mod_fun(double *state, double *out_6557368431862547615) {
  H_mod_fun(state, out_6557368431862547615);
}
void pose_f_fun(double *state, double dt, double *out_8766002253507214463) {
  f_fun(state,  dt, out_8766002253507214463);
}
void pose_F_fun(double *state, double dt, double *out_7027423975176096545) {
  F_fun(state,  dt, out_7027423975176096545);
}
void pose_h_4(double *state, double *unused, double *out_8406635548758778985) {
  h_4(state, unused, out_8406635548758778985);
}
void pose_H_4(double *state, double *unused, double *out_9087533728568900293) {
  H_4(state, unused, out_9087533728568900293);
}
void pose_h_10(double *state, double *unused, double *out_4724563756245089329) {
  h_10(state, unused, out_4724563756245089329);
}
void pose_H_10(double *state, double *unused, double *out_151772769759508374) {
  H_10(state, unused, out_151772769759508374);
}
void pose_h_13(double *state, double *unused, double *out_916448766757343904) {
  h_13(state, unused, out_916448766757343904);
}
void pose_H_13(double *state, double *unused, double *out_1748579136823950394) {
  H_13(state, unused, out_1748579136823950394);
}
void pose_h_14(double *state, double *unused, double *out_4320749477702954633) {
  h_14(state, unused, out_4320749477702954633);
}
void pose_H_14(double *state, double *unused, double *out_6004745296273527997) {
  H_14(state, unused, out_6004745296273527997);
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
