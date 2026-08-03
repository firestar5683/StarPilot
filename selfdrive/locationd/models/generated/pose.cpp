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
void err_fun(double *nom_x, double *delta_x, double *out_5143015347590812681) {
   out_5143015347590812681[0] = delta_x[0] + nom_x[0];
   out_5143015347590812681[1] = delta_x[1] + nom_x[1];
   out_5143015347590812681[2] = delta_x[2] + nom_x[2];
   out_5143015347590812681[3] = delta_x[3] + nom_x[3];
   out_5143015347590812681[4] = delta_x[4] + nom_x[4];
   out_5143015347590812681[5] = delta_x[5] + nom_x[5];
   out_5143015347590812681[6] = delta_x[6] + nom_x[6];
   out_5143015347590812681[7] = delta_x[7] + nom_x[7];
   out_5143015347590812681[8] = delta_x[8] + nom_x[8];
   out_5143015347590812681[9] = delta_x[9] + nom_x[9];
   out_5143015347590812681[10] = delta_x[10] + nom_x[10];
   out_5143015347590812681[11] = delta_x[11] + nom_x[11];
   out_5143015347590812681[12] = delta_x[12] + nom_x[12];
   out_5143015347590812681[13] = delta_x[13] + nom_x[13];
   out_5143015347590812681[14] = delta_x[14] + nom_x[14];
   out_5143015347590812681[15] = delta_x[15] + nom_x[15];
   out_5143015347590812681[16] = delta_x[16] + nom_x[16];
   out_5143015347590812681[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1498290725825032559) {
   out_1498290725825032559[0] = -nom_x[0] + true_x[0];
   out_1498290725825032559[1] = -nom_x[1] + true_x[1];
   out_1498290725825032559[2] = -nom_x[2] + true_x[2];
   out_1498290725825032559[3] = -nom_x[3] + true_x[3];
   out_1498290725825032559[4] = -nom_x[4] + true_x[4];
   out_1498290725825032559[5] = -nom_x[5] + true_x[5];
   out_1498290725825032559[6] = -nom_x[6] + true_x[6];
   out_1498290725825032559[7] = -nom_x[7] + true_x[7];
   out_1498290725825032559[8] = -nom_x[8] + true_x[8];
   out_1498290725825032559[9] = -nom_x[9] + true_x[9];
   out_1498290725825032559[10] = -nom_x[10] + true_x[10];
   out_1498290725825032559[11] = -nom_x[11] + true_x[11];
   out_1498290725825032559[12] = -nom_x[12] + true_x[12];
   out_1498290725825032559[13] = -nom_x[13] + true_x[13];
   out_1498290725825032559[14] = -nom_x[14] + true_x[14];
   out_1498290725825032559[15] = -nom_x[15] + true_x[15];
   out_1498290725825032559[16] = -nom_x[16] + true_x[16];
   out_1498290725825032559[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4606755190645614426) {
   out_4606755190645614426[0] = 1.0;
   out_4606755190645614426[1] = 0.0;
   out_4606755190645614426[2] = 0.0;
   out_4606755190645614426[3] = 0.0;
   out_4606755190645614426[4] = 0.0;
   out_4606755190645614426[5] = 0.0;
   out_4606755190645614426[6] = 0.0;
   out_4606755190645614426[7] = 0.0;
   out_4606755190645614426[8] = 0.0;
   out_4606755190645614426[9] = 0.0;
   out_4606755190645614426[10] = 0.0;
   out_4606755190645614426[11] = 0.0;
   out_4606755190645614426[12] = 0.0;
   out_4606755190645614426[13] = 0.0;
   out_4606755190645614426[14] = 0.0;
   out_4606755190645614426[15] = 0.0;
   out_4606755190645614426[16] = 0.0;
   out_4606755190645614426[17] = 0.0;
   out_4606755190645614426[18] = 0.0;
   out_4606755190645614426[19] = 1.0;
   out_4606755190645614426[20] = 0.0;
   out_4606755190645614426[21] = 0.0;
   out_4606755190645614426[22] = 0.0;
   out_4606755190645614426[23] = 0.0;
   out_4606755190645614426[24] = 0.0;
   out_4606755190645614426[25] = 0.0;
   out_4606755190645614426[26] = 0.0;
   out_4606755190645614426[27] = 0.0;
   out_4606755190645614426[28] = 0.0;
   out_4606755190645614426[29] = 0.0;
   out_4606755190645614426[30] = 0.0;
   out_4606755190645614426[31] = 0.0;
   out_4606755190645614426[32] = 0.0;
   out_4606755190645614426[33] = 0.0;
   out_4606755190645614426[34] = 0.0;
   out_4606755190645614426[35] = 0.0;
   out_4606755190645614426[36] = 0.0;
   out_4606755190645614426[37] = 0.0;
   out_4606755190645614426[38] = 1.0;
   out_4606755190645614426[39] = 0.0;
   out_4606755190645614426[40] = 0.0;
   out_4606755190645614426[41] = 0.0;
   out_4606755190645614426[42] = 0.0;
   out_4606755190645614426[43] = 0.0;
   out_4606755190645614426[44] = 0.0;
   out_4606755190645614426[45] = 0.0;
   out_4606755190645614426[46] = 0.0;
   out_4606755190645614426[47] = 0.0;
   out_4606755190645614426[48] = 0.0;
   out_4606755190645614426[49] = 0.0;
   out_4606755190645614426[50] = 0.0;
   out_4606755190645614426[51] = 0.0;
   out_4606755190645614426[52] = 0.0;
   out_4606755190645614426[53] = 0.0;
   out_4606755190645614426[54] = 0.0;
   out_4606755190645614426[55] = 0.0;
   out_4606755190645614426[56] = 0.0;
   out_4606755190645614426[57] = 1.0;
   out_4606755190645614426[58] = 0.0;
   out_4606755190645614426[59] = 0.0;
   out_4606755190645614426[60] = 0.0;
   out_4606755190645614426[61] = 0.0;
   out_4606755190645614426[62] = 0.0;
   out_4606755190645614426[63] = 0.0;
   out_4606755190645614426[64] = 0.0;
   out_4606755190645614426[65] = 0.0;
   out_4606755190645614426[66] = 0.0;
   out_4606755190645614426[67] = 0.0;
   out_4606755190645614426[68] = 0.0;
   out_4606755190645614426[69] = 0.0;
   out_4606755190645614426[70] = 0.0;
   out_4606755190645614426[71] = 0.0;
   out_4606755190645614426[72] = 0.0;
   out_4606755190645614426[73] = 0.0;
   out_4606755190645614426[74] = 0.0;
   out_4606755190645614426[75] = 0.0;
   out_4606755190645614426[76] = 1.0;
   out_4606755190645614426[77] = 0.0;
   out_4606755190645614426[78] = 0.0;
   out_4606755190645614426[79] = 0.0;
   out_4606755190645614426[80] = 0.0;
   out_4606755190645614426[81] = 0.0;
   out_4606755190645614426[82] = 0.0;
   out_4606755190645614426[83] = 0.0;
   out_4606755190645614426[84] = 0.0;
   out_4606755190645614426[85] = 0.0;
   out_4606755190645614426[86] = 0.0;
   out_4606755190645614426[87] = 0.0;
   out_4606755190645614426[88] = 0.0;
   out_4606755190645614426[89] = 0.0;
   out_4606755190645614426[90] = 0.0;
   out_4606755190645614426[91] = 0.0;
   out_4606755190645614426[92] = 0.0;
   out_4606755190645614426[93] = 0.0;
   out_4606755190645614426[94] = 0.0;
   out_4606755190645614426[95] = 1.0;
   out_4606755190645614426[96] = 0.0;
   out_4606755190645614426[97] = 0.0;
   out_4606755190645614426[98] = 0.0;
   out_4606755190645614426[99] = 0.0;
   out_4606755190645614426[100] = 0.0;
   out_4606755190645614426[101] = 0.0;
   out_4606755190645614426[102] = 0.0;
   out_4606755190645614426[103] = 0.0;
   out_4606755190645614426[104] = 0.0;
   out_4606755190645614426[105] = 0.0;
   out_4606755190645614426[106] = 0.0;
   out_4606755190645614426[107] = 0.0;
   out_4606755190645614426[108] = 0.0;
   out_4606755190645614426[109] = 0.0;
   out_4606755190645614426[110] = 0.0;
   out_4606755190645614426[111] = 0.0;
   out_4606755190645614426[112] = 0.0;
   out_4606755190645614426[113] = 0.0;
   out_4606755190645614426[114] = 1.0;
   out_4606755190645614426[115] = 0.0;
   out_4606755190645614426[116] = 0.0;
   out_4606755190645614426[117] = 0.0;
   out_4606755190645614426[118] = 0.0;
   out_4606755190645614426[119] = 0.0;
   out_4606755190645614426[120] = 0.0;
   out_4606755190645614426[121] = 0.0;
   out_4606755190645614426[122] = 0.0;
   out_4606755190645614426[123] = 0.0;
   out_4606755190645614426[124] = 0.0;
   out_4606755190645614426[125] = 0.0;
   out_4606755190645614426[126] = 0.0;
   out_4606755190645614426[127] = 0.0;
   out_4606755190645614426[128] = 0.0;
   out_4606755190645614426[129] = 0.0;
   out_4606755190645614426[130] = 0.0;
   out_4606755190645614426[131] = 0.0;
   out_4606755190645614426[132] = 0.0;
   out_4606755190645614426[133] = 1.0;
   out_4606755190645614426[134] = 0.0;
   out_4606755190645614426[135] = 0.0;
   out_4606755190645614426[136] = 0.0;
   out_4606755190645614426[137] = 0.0;
   out_4606755190645614426[138] = 0.0;
   out_4606755190645614426[139] = 0.0;
   out_4606755190645614426[140] = 0.0;
   out_4606755190645614426[141] = 0.0;
   out_4606755190645614426[142] = 0.0;
   out_4606755190645614426[143] = 0.0;
   out_4606755190645614426[144] = 0.0;
   out_4606755190645614426[145] = 0.0;
   out_4606755190645614426[146] = 0.0;
   out_4606755190645614426[147] = 0.0;
   out_4606755190645614426[148] = 0.0;
   out_4606755190645614426[149] = 0.0;
   out_4606755190645614426[150] = 0.0;
   out_4606755190645614426[151] = 0.0;
   out_4606755190645614426[152] = 1.0;
   out_4606755190645614426[153] = 0.0;
   out_4606755190645614426[154] = 0.0;
   out_4606755190645614426[155] = 0.0;
   out_4606755190645614426[156] = 0.0;
   out_4606755190645614426[157] = 0.0;
   out_4606755190645614426[158] = 0.0;
   out_4606755190645614426[159] = 0.0;
   out_4606755190645614426[160] = 0.0;
   out_4606755190645614426[161] = 0.0;
   out_4606755190645614426[162] = 0.0;
   out_4606755190645614426[163] = 0.0;
   out_4606755190645614426[164] = 0.0;
   out_4606755190645614426[165] = 0.0;
   out_4606755190645614426[166] = 0.0;
   out_4606755190645614426[167] = 0.0;
   out_4606755190645614426[168] = 0.0;
   out_4606755190645614426[169] = 0.0;
   out_4606755190645614426[170] = 0.0;
   out_4606755190645614426[171] = 1.0;
   out_4606755190645614426[172] = 0.0;
   out_4606755190645614426[173] = 0.0;
   out_4606755190645614426[174] = 0.0;
   out_4606755190645614426[175] = 0.0;
   out_4606755190645614426[176] = 0.0;
   out_4606755190645614426[177] = 0.0;
   out_4606755190645614426[178] = 0.0;
   out_4606755190645614426[179] = 0.0;
   out_4606755190645614426[180] = 0.0;
   out_4606755190645614426[181] = 0.0;
   out_4606755190645614426[182] = 0.0;
   out_4606755190645614426[183] = 0.0;
   out_4606755190645614426[184] = 0.0;
   out_4606755190645614426[185] = 0.0;
   out_4606755190645614426[186] = 0.0;
   out_4606755190645614426[187] = 0.0;
   out_4606755190645614426[188] = 0.0;
   out_4606755190645614426[189] = 0.0;
   out_4606755190645614426[190] = 1.0;
   out_4606755190645614426[191] = 0.0;
   out_4606755190645614426[192] = 0.0;
   out_4606755190645614426[193] = 0.0;
   out_4606755190645614426[194] = 0.0;
   out_4606755190645614426[195] = 0.0;
   out_4606755190645614426[196] = 0.0;
   out_4606755190645614426[197] = 0.0;
   out_4606755190645614426[198] = 0.0;
   out_4606755190645614426[199] = 0.0;
   out_4606755190645614426[200] = 0.0;
   out_4606755190645614426[201] = 0.0;
   out_4606755190645614426[202] = 0.0;
   out_4606755190645614426[203] = 0.0;
   out_4606755190645614426[204] = 0.0;
   out_4606755190645614426[205] = 0.0;
   out_4606755190645614426[206] = 0.0;
   out_4606755190645614426[207] = 0.0;
   out_4606755190645614426[208] = 0.0;
   out_4606755190645614426[209] = 1.0;
   out_4606755190645614426[210] = 0.0;
   out_4606755190645614426[211] = 0.0;
   out_4606755190645614426[212] = 0.0;
   out_4606755190645614426[213] = 0.0;
   out_4606755190645614426[214] = 0.0;
   out_4606755190645614426[215] = 0.0;
   out_4606755190645614426[216] = 0.0;
   out_4606755190645614426[217] = 0.0;
   out_4606755190645614426[218] = 0.0;
   out_4606755190645614426[219] = 0.0;
   out_4606755190645614426[220] = 0.0;
   out_4606755190645614426[221] = 0.0;
   out_4606755190645614426[222] = 0.0;
   out_4606755190645614426[223] = 0.0;
   out_4606755190645614426[224] = 0.0;
   out_4606755190645614426[225] = 0.0;
   out_4606755190645614426[226] = 0.0;
   out_4606755190645614426[227] = 0.0;
   out_4606755190645614426[228] = 1.0;
   out_4606755190645614426[229] = 0.0;
   out_4606755190645614426[230] = 0.0;
   out_4606755190645614426[231] = 0.0;
   out_4606755190645614426[232] = 0.0;
   out_4606755190645614426[233] = 0.0;
   out_4606755190645614426[234] = 0.0;
   out_4606755190645614426[235] = 0.0;
   out_4606755190645614426[236] = 0.0;
   out_4606755190645614426[237] = 0.0;
   out_4606755190645614426[238] = 0.0;
   out_4606755190645614426[239] = 0.0;
   out_4606755190645614426[240] = 0.0;
   out_4606755190645614426[241] = 0.0;
   out_4606755190645614426[242] = 0.0;
   out_4606755190645614426[243] = 0.0;
   out_4606755190645614426[244] = 0.0;
   out_4606755190645614426[245] = 0.0;
   out_4606755190645614426[246] = 0.0;
   out_4606755190645614426[247] = 1.0;
   out_4606755190645614426[248] = 0.0;
   out_4606755190645614426[249] = 0.0;
   out_4606755190645614426[250] = 0.0;
   out_4606755190645614426[251] = 0.0;
   out_4606755190645614426[252] = 0.0;
   out_4606755190645614426[253] = 0.0;
   out_4606755190645614426[254] = 0.0;
   out_4606755190645614426[255] = 0.0;
   out_4606755190645614426[256] = 0.0;
   out_4606755190645614426[257] = 0.0;
   out_4606755190645614426[258] = 0.0;
   out_4606755190645614426[259] = 0.0;
   out_4606755190645614426[260] = 0.0;
   out_4606755190645614426[261] = 0.0;
   out_4606755190645614426[262] = 0.0;
   out_4606755190645614426[263] = 0.0;
   out_4606755190645614426[264] = 0.0;
   out_4606755190645614426[265] = 0.0;
   out_4606755190645614426[266] = 1.0;
   out_4606755190645614426[267] = 0.0;
   out_4606755190645614426[268] = 0.0;
   out_4606755190645614426[269] = 0.0;
   out_4606755190645614426[270] = 0.0;
   out_4606755190645614426[271] = 0.0;
   out_4606755190645614426[272] = 0.0;
   out_4606755190645614426[273] = 0.0;
   out_4606755190645614426[274] = 0.0;
   out_4606755190645614426[275] = 0.0;
   out_4606755190645614426[276] = 0.0;
   out_4606755190645614426[277] = 0.0;
   out_4606755190645614426[278] = 0.0;
   out_4606755190645614426[279] = 0.0;
   out_4606755190645614426[280] = 0.0;
   out_4606755190645614426[281] = 0.0;
   out_4606755190645614426[282] = 0.0;
   out_4606755190645614426[283] = 0.0;
   out_4606755190645614426[284] = 0.0;
   out_4606755190645614426[285] = 1.0;
   out_4606755190645614426[286] = 0.0;
   out_4606755190645614426[287] = 0.0;
   out_4606755190645614426[288] = 0.0;
   out_4606755190645614426[289] = 0.0;
   out_4606755190645614426[290] = 0.0;
   out_4606755190645614426[291] = 0.0;
   out_4606755190645614426[292] = 0.0;
   out_4606755190645614426[293] = 0.0;
   out_4606755190645614426[294] = 0.0;
   out_4606755190645614426[295] = 0.0;
   out_4606755190645614426[296] = 0.0;
   out_4606755190645614426[297] = 0.0;
   out_4606755190645614426[298] = 0.0;
   out_4606755190645614426[299] = 0.0;
   out_4606755190645614426[300] = 0.0;
   out_4606755190645614426[301] = 0.0;
   out_4606755190645614426[302] = 0.0;
   out_4606755190645614426[303] = 0.0;
   out_4606755190645614426[304] = 1.0;
   out_4606755190645614426[305] = 0.0;
   out_4606755190645614426[306] = 0.0;
   out_4606755190645614426[307] = 0.0;
   out_4606755190645614426[308] = 0.0;
   out_4606755190645614426[309] = 0.0;
   out_4606755190645614426[310] = 0.0;
   out_4606755190645614426[311] = 0.0;
   out_4606755190645614426[312] = 0.0;
   out_4606755190645614426[313] = 0.0;
   out_4606755190645614426[314] = 0.0;
   out_4606755190645614426[315] = 0.0;
   out_4606755190645614426[316] = 0.0;
   out_4606755190645614426[317] = 0.0;
   out_4606755190645614426[318] = 0.0;
   out_4606755190645614426[319] = 0.0;
   out_4606755190645614426[320] = 0.0;
   out_4606755190645614426[321] = 0.0;
   out_4606755190645614426[322] = 0.0;
   out_4606755190645614426[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8576950781836710085) {
   out_8576950781836710085[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8576950781836710085[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8576950781836710085[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8576950781836710085[3] = dt*state[12] + state[3];
   out_8576950781836710085[4] = dt*state[13] + state[4];
   out_8576950781836710085[5] = dt*state[14] + state[5];
   out_8576950781836710085[6] = state[6];
   out_8576950781836710085[7] = state[7];
   out_8576950781836710085[8] = state[8];
   out_8576950781836710085[9] = state[9];
   out_8576950781836710085[10] = state[10];
   out_8576950781836710085[11] = state[11];
   out_8576950781836710085[12] = state[12];
   out_8576950781836710085[13] = state[13];
   out_8576950781836710085[14] = state[14];
   out_8576950781836710085[15] = state[15];
   out_8576950781836710085[16] = state[16];
   out_8576950781836710085[17] = state[17];
}
void F_fun(double *state, double dt, double *out_9071365926554278405) {
   out_9071365926554278405[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9071365926554278405[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9071365926554278405[2] = 0;
   out_9071365926554278405[3] = 0;
   out_9071365926554278405[4] = 0;
   out_9071365926554278405[5] = 0;
   out_9071365926554278405[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9071365926554278405[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9071365926554278405[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9071365926554278405[9] = 0;
   out_9071365926554278405[10] = 0;
   out_9071365926554278405[11] = 0;
   out_9071365926554278405[12] = 0;
   out_9071365926554278405[13] = 0;
   out_9071365926554278405[14] = 0;
   out_9071365926554278405[15] = 0;
   out_9071365926554278405[16] = 0;
   out_9071365926554278405[17] = 0;
   out_9071365926554278405[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9071365926554278405[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9071365926554278405[20] = 0;
   out_9071365926554278405[21] = 0;
   out_9071365926554278405[22] = 0;
   out_9071365926554278405[23] = 0;
   out_9071365926554278405[24] = 0;
   out_9071365926554278405[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9071365926554278405[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9071365926554278405[27] = 0;
   out_9071365926554278405[28] = 0;
   out_9071365926554278405[29] = 0;
   out_9071365926554278405[30] = 0;
   out_9071365926554278405[31] = 0;
   out_9071365926554278405[32] = 0;
   out_9071365926554278405[33] = 0;
   out_9071365926554278405[34] = 0;
   out_9071365926554278405[35] = 0;
   out_9071365926554278405[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9071365926554278405[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9071365926554278405[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9071365926554278405[39] = 0;
   out_9071365926554278405[40] = 0;
   out_9071365926554278405[41] = 0;
   out_9071365926554278405[42] = 0;
   out_9071365926554278405[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9071365926554278405[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9071365926554278405[45] = 0;
   out_9071365926554278405[46] = 0;
   out_9071365926554278405[47] = 0;
   out_9071365926554278405[48] = 0;
   out_9071365926554278405[49] = 0;
   out_9071365926554278405[50] = 0;
   out_9071365926554278405[51] = 0;
   out_9071365926554278405[52] = 0;
   out_9071365926554278405[53] = 0;
   out_9071365926554278405[54] = 0;
   out_9071365926554278405[55] = 0;
   out_9071365926554278405[56] = 0;
   out_9071365926554278405[57] = 1;
   out_9071365926554278405[58] = 0;
   out_9071365926554278405[59] = 0;
   out_9071365926554278405[60] = 0;
   out_9071365926554278405[61] = 0;
   out_9071365926554278405[62] = 0;
   out_9071365926554278405[63] = 0;
   out_9071365926554278405[64] = 0;
   out_9071365926554278405[65] = 0;
   out_9071365926554278405[66] = dt;
   out_9071365926554278405[67] = 0;
   out_9071365926554278405[68] = 0;
   out_9071365926554278405[69] = 0;
   out_9071365926554278405[70] = 0;
   out_9071365926554278405[71] = 0;
   out_9071365926554278405[72] = 0;
   out_9071365926554278405[73] = 0;
   out_9071365926554278405[74] = 0;
   out_9071365926554278405[75] = 0;
   out_9071365926554278405[76] = 1;
   out_9071365926554278405[77] = 0;
   out_9071365926554278405[78] = 0;
   out_9071365926554278405[79] = 0;
   out_9071365926554278405[80] = 0;
   out_9071365926554278405[81] = 0;
   out_9071365926554278405[82] = 0;
   out_9071365926554278405[83] = 0;
   out_9071365926554278405[84] = 0;
   out_9071365926554278405[85] = dt;
   out_9071365926554278405[86] = 0;
   out_9071365926554278405[87] = 0;
   out_9071365926554278405[88] = 0;
   out_9071365926554278405[89] = 0;
   out_9071365926554278405[90] = 0;
   out_9071365926554278405[91] = 0;
   out_9071365926554278405[92] = 0;
   out_9071365926554278405[93] = 0;
   out_9071365926554278405[94] = 0;
   out_9071365926554278405[95] = 1;
   out_9071365926554278405[96] = 0;
   out_9071365926554278405[97] = 0;
   out_9071365926554278405[98] = 0;
   out_9071365926554278405[99] = 0;
   out_9071365926554278405[100] = 0;
   out_9071365926554278405[101] = 0;
   out_9071365926554278405[102] = 0;
   out_9071365926554278405[103] = 0;
   out_9071365926554278405[104] = dt;
   out_9071365926554278405[105] = 0;
   out_9071365926554278405[106] = 0;
   out_9071365926554278405[107] = 0;
   out_9071365926554278405[108] = 0;
   out_9071365926554278405[109] = 0;
   out_9071365926554278405[110] = 0;
   out_9071365926554278405[111] = 0;
   out_9071365926554278405[112] = 0;
   out_9071365926554278405[113] = 0;
   out_9071365926554278405[114] = 1;
   out_9071365926554278405[115] = 0;
   out_9071365926554278405[116] = 0;
   out_9071365926554278405[117] = 0;
   out_9071365926554278405[118] = 0;
   out_9071365926554278405[119] = 0;
   out_9071365926554278405[120] = 0;
   out_9071365926554278405[121] = 0;
   out_9071365926554278405[122] = 0;
   out_9071365926554278405[123] = 0;
   out_9071365926554278405[124] = 0;
   out_9071365926554278405[125] = 0;
   out_9071365926554278405[126] = 0;
   out_9071365926554278405[127] = 0;
   out_9071365926554278405[128] = 0;
   out_9071365926554278405[129] = 0;
   out_9071365926554278405[130] = 0;
   out_9071365926554278405[131] = 0;
   out_9071365926554278405[132] = 0;
   out_9071365926554278405[133] = 1;
   out_9071365926554278405[134] = 0;
   out_9071365926554278405[135] = 0;
   out_9071365926554278405[136] = 0;
   out_9071365926554278405[137] = 0;
   out_9071365926554278405[138] = 0;
   out_9071365926554278405[139] = 0;
   out_9071365926554278405[140] = 0;
   out_9071365926554278405[141] = 0;
   out_9071365926554278405[142] = 0;
   out_9071365926554278405[143] = 0;
   out_9071365926554278405[144] = 0;
   out_9071365926554278405[145] = 0;
   out_9071365926554278405[146] = 0;
   out_9071365926554278405[147] = 0;
   out_9071365926554278405[148] = 0;
   out_9071365926554278405[149] = 0;
   out_9071365926554278405[150] = 0;
   out_9071365926554278405[151] = 0;
   out_9071365926554278405[152] = 1;
   out_9071365926554278405[153] = 0;
   out_9071365926554278405[154] = 0;
   out_9071365926554278405[155] = 0;
   out_9071365926554278405[156] = 0;
   out_9071365926554278405[157] = 0;
   out_9071365926554278405[158] = 0;
   out_9071365926554278405[159] = 0;
   out_9071365926554278405[160] = 0;
   out_9071365926554278405[161] = 0;
   out_9071365926554278405[162] = 0;
   out_9071365926554278405[163] = 0;
   out_9071365926554278405[164] = 0;
   out_9071365926554278405[165] = 0;
   out_9071365926554278405[166] = 0;
   out_9071365926554278405[167] = 0;
   out_9071365926554278405[168] = 0;
   out_9071365926554278405[169] = 0;
   out_9071365926554278405[170] = 0;
   out_9071365926554278405[171] = 1;
   out_9071365926554278405[172] = 0;
   out_9071365926554278405[173] = 0;
   out_9071365926554278405[174] = 0;
   out_9071365926554278405[175] = 0;
   out_9071365926554278405[176] = 0;
   out_9071365926554278405[177] = 0;
   out_9071365926554278405[178] = 0;
   out_9071365926554278405[179] = 0;
   out_9071365926554278405[180] = 0;
   out_9071365926554278405[181] = 0;
   out_9071365926554278405[182] = 0;
   out_9071365926554278405[183] = 0;
   out_9071365926554278405[184] = 0;
   out_9071365926554278405[185] = 0;
   out_9071365926554278405[186] = 0;
   out_9071365926554278405[187] = 0;
   out_9071365926554278405[188] = 0;
   out_9071365926554278405[189] = 0;
   out_9071365926554278405[190] = 1;
   out_9071365926554278405[191] = 0;
   out_9071365926554278405[192] = 0;
   out_9071365926554278405[193] = 0;
   out_9071365926554278405[194] = 0;
   out_9071365926554278405[195] = 0;
   out_9071365926554278405[196] = 0;
   out_9071365926554278405[197] = 0;
   out_9071365926554278405[198] = 0;
   out_9071365926554278405[199] = 0;
   out_9071365926554278405[200] = 0;
   out_9071365926554278405[201] = 0;
   out_9071365926554278405[202] = 0;
   out_9071365926554278405[203] = 0;
   out_9071365926554278405[204] = 0;
   out_9071365926554278405[205] = 0;
   out_9071365926554278405[206] = 0;
   out_9071365926554278405[207] = 0;
   out_9071365926554278405[208] = 0;
   out_9071365926554278405[209] = 1;
   out_9071365926554278405[210] = 0;
   out_9071365926554278405[211] = 0;
   out_9071365926554278405[212] = 0;
   out_9071365926554278405[213] = 0;
   out_9071365926554278405[214] = 0;
   out_9071365926554278405[215] = 0;
   out_9071365926554278405[216] = 0;
   out_9071365926554278405[217] = 0;
   out_9071365926554278405[218] = 0;
   out_9071365926554278405[219] = 0;
   out_9071365926554278405[220] = 0;
   out_9071365926554278405[221] = 0;
   out_9071365926554278405[222] = 0;
   out_9071365926554278405[223] = 0;
   out_9071365926554278405[224] = 0;
   out_9071365926554278405[225] = 0;
   out_9071365926554278405[226] = 0;
   out_9071365926554278405[227] = 0;
   out_9071365926554278405[228] = 1;
   out_9071365926554278405[229] = 0;
   out_9071365926554278405[230] = 0;
   out_9071365926554278405[231] = 0;
   out_9071365926554278405[232] = 0;
   out_9071365926554278405[233] = 0;
   out_9071365926554278405[234] = 0;
   out_9071365926554278405[235] = 0;
   out_9071365926554278405[236] = 0;
   out_9071365926554278405[237] = 0;
   out_9071365926554278405[238] = 0;
   out_9071365926554278405[239] = 0;
   out_9071365926554278405[240] = 0;
   out_9071365926554278405[241] = 0;
   out_9071365926554278405[242] = 0;
   out_9071365926554278405[243] = 0;
   out_9071365926554278405[244] = 0;
   out_9071365926554278405[245] = 0;
   out_9071365926554278405[246] = 0;
   out_9071365926554278405[247] = 1;
   out_9071365926554278405[248] = 0;
   out_9071365926554278405[249] = 0;
   out_9071365926554278405[250] = 0;
   out_9071365926554278405[251] = 0;
   out_9071365926554278405[252] = 0;
   out_9071365926554278405[253] = 0;
   out_9071365926554278405[254] = 0;
   out_9071365926554278405[255] = 0;
   out_9071365926554278405[256] = 0;
   out_9071365926554278405[257] = 0;
   out_9071365926554278405[258] = 0;
   out_9071365926554278405[259] = 0;
   out_9071365926554278405[260] = 0;
   out_9071365926554278405[261] = 0;
   out_9071365926554278405[262] = 0;
   out_9071365926554278405[263] = 0;
   out_9071365926554278405[264] = 0;
   out_9071365926554278405[265] = 0;
   out_9071365926554278405[266] = 1;
   out_9071365926554278405[267] = 0;
   out_9071365926554278405[268] = 0;
   out_9071365926554278405[269] = 0;
   out_9071365926554278405[270] = 0;
   out_9071365926554278405[271] = 0;
   out_9071365926554278405[272] = 0;
   out_9071365926554278405[273] = 0;
   out_9071365926554278405[274] = 0;
   out_9071365926554278405[275] = 0;
   out_9071365926554278405[276] = 0;
   out_9071365926554278405[277] = 0;
   out_9071365926554278405[278] = 0;
   out_9071365926554278405[279] = 0;
   out_9071365926554278405[280] = 0;
   out_9071365926554278405[281] = 0;
   out_9071365926554278405[282] = 0;
   out_9071365926554278405[283] = 0;
   out_9071365926554278405[284] = 0;
   out_9071365926554278405[285] = 1;
   out_9071365926554278405[286] = 0;
   out_9071365926554278405[287] = 0;
   out_9071365926554278405[288] = 0;
   out_9071365926554278405[289] = 0;
   out_9071365926554278405[290] = 0;
   out_9071365926554278405[291] = 0;
   out_9071365926554278405[292] = 0;
   out_9071365926554278405[293] = 0;
   out_9071365926554278405[294] = 0;
   out_9071365926554278405[295] = 0;
   out_9071365926554278405[296] = 0;
   out_9071365926554278405[297] = 0;
   out_9071365926554278405[298] = 0;
   out_9071365926554278405[299] = 0;
   out_9071365926554278405[300] = 0;
   out_9071365926554278405[301] = 0;
   out_9071365926554278405[302] = 0;
   out_9071365926554278405[303] = 0;
   out_9071365926554278405[304] = 1;
   out_9071365926554278405[305] = 0;
   out_9071365926554278405[306] = 0;
   out_9071365926554278405[307] = 0;
   out_9071365926554278405[308] = 0;
   out_9071365926554278405[309] = 0;
   out_9071365926554278405[310] = 0;
   out_9071365926554278405[311] = 0;
   out_9071365926554278405[312] = 0;
   out_9071365926554278405[313] = 0;
   out_9071365926554278405[314] = 0;
   out_9071365926554278405[315] = 0;
   out_9071365926554278405[316] = 0;
   out_9071365926554278405[317] = 0;
   out_9071365926554278405[318] = 0;
   out_9071365926554278405[319] = 0;
   out_9071365926554278405[320] = 0;
   out_9071365926554278405[321] = 0;
   out_9071365926554278405[322] = 0;
   out_9071365926554278405[323] = 1;
}
void h_4(double *state, double *unused, double *out_7694457163636602289) {
   out_7694457163636602289[0] = state[6] + state[9];
   out_7694457163636602289[1] = state[7] + state[10];
   out_7694457163636602289[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7880977269436563679) {
   out_7880977269436563679[0] = 0;
   out_7880977269436563679[1] = 0;
   out_7880977269436563679[2] = 0;
   out_7880977269436563679[3] = 0;
   out_7880977269436563679[4] = 0;
   out_7880977269436563679[5] = 0;
   out_7880977269436563679[6] = 1;
   out_7880977269436563679[7] = 0;
   out_7880977269436563679[8] = 0;
   out_7880977269436563679[9] = 1;
   out_7880977269436563679[10] = 0;
   out_7880977269436563679[11] = 0;
   out_7880977269436563679[12] = 0;
   out_7880977269436563679[13] = 0;
   out_7880977269436563679[14] = 0;
   out_7880977269436563679[15] = 0;
   out_7880977269436563679[16] = 0;
   out_7880977269436563679[17] = 0;
   out_7880977269436563679[18] = 0;
   out_7880977269436563679[19] = 0;
   out_7880977269436563679[20] = 0;
   out_7880977269436563679[21] = 0;
   out_7880977269436563679[22] = 0;
   out_7880977269436563679[23] = 0;
   out_7880977269436563679[24] = 0;
   out_7880977269436563679[25] = 1;
   out_7880977269436563679[26] = 0;
   out_7880977269436563679[27] = 0;
   out_7880977269436563679[28] = 1;
   out_7880977269436563679[29] = 0;
   out_7880977269436563679[30] = 0;
   out_7880977269436563679[31] = 0;
   out_7880977269436563679[32] = 0;
   out_7880977269436563679[33] = 0;
   out_7880977269436563679[34] = 0;
   out_7880977269436563679[35] = 0;
   out_7880977269436563679[36] = 0;
   out_7880977269436563679[37] = 0;
   out_7880977269436563679[38] = 0;
   out_7880977269436563679[39] = 0;
   out_7880977269436563679[40] = 0;
   out_7880977269436563679[41] = 0;
   out_7880977269436563679[42] = 0;
   out_7880977269436563679[43] = 0;
   out_7880977269436563679[44] = 1;
   out_7880977269436563679[45] = 0;
   out_7880977269436563679[46] = 0;
   out_7880977269436563679[47] = 1;
   out_7880977269436563679[48] = 0;
   out_7880977269436563679[49] = 0;
   out_7880977269436563679[50] = 0;
   out_7880977269436563679[51] = 0;
   out_7880977269436563679[52] = 0;
   out_7880977269436563679[53] = 0;
}
void h_10(double *state, double *unused, double *out_5236443719394936462) {
   out_5236443719394936462[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5236443719394936462[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5236443719394936462[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8689295297570059510) {
   out_8689295297570059510[0] = 0;
   out_8689295297570059510[1] = 9.8100000000000005*cos(state[1]);
   out_8689295297570059510[2] = 0;
   out_8689295297570059510[3] = 0;
   out_8689295297570059510[4] = -state[8];
   out_8689295297570059510[5] = state[7];
   out_8689295297570059510[6] = 0;
   out_8689295297570059510[7] = state[5];
   out_8689295297570059510[8] = -state[4];
   out_8689295297570059510[9] = 0;
   out_8689295297570059510[10] = 0;
   out_8689295297570059510[11] = 0;
   out_8689295297570059510[12] = 1;
   out_8689295297570059510[13] = 0;
   out_8689295297570059510[14] = 0;
   out_8689295297570059510[15] = 1;
   out_8689295297570059510[16] = 0;
   out_8689295297570059510[17] = 0;
   out_8689295297570059510[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8689295297570059510[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8689295297570059510[20] = 0;
   out_8689295297570059510[21] = state[8];
   out_8689295297570059510[22] = 0;
   out_8689295297570059510[23] = -state[6];
   out_8689295297570059510[24] = -state[5];
   out_8689295297570059510[25] = 0;
   out_8689295297570059510[26] = state[3];
   out_8689295297570059510[27] = 0;
   out_8689295297570059510[28] = 0;
   out_8689295297570059510[29] = 0;
   out_8689295297570059510[30] = 0;
   out_8689295297570059510[31] = 1;
   out_8689295297570059510[32] = 0;
   out_8689295297570059510[33] = 0;
   out_8689295297570059510[34] = 1;
   out_8689295297570059510[35] = 0;
   out_8689295297570059510[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8689295297570059510[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8689295297570059510[38] = 0;
   out_8689295297570059510[39] = -state[7];
   out_8689295297570059510[40] = state[6];
   out_8689295297570059510[41] = 0;
   out_8689295297570059510[42] = state[4];
   out_8689295297570059510[43] = -state[3];
   out_8689295297570059510[44] = 0;
   out_8689295297570059510[45] = 0;
   out_8689295297570059510[46] = 0;
   out_8689295297570059510[47] = 0;
   out_8689295297570059510[48] = 0;
   out_8689295297570059510[49] = 0;
   out_8689295297570059510[50] = 1;
   out_8689295297570059510[51] = 0;
   out_8689295297570059510[52] = 0;
   out_8689295297570059510[53] = 1;
}
void h_13(double *state, double *unused, double *out_9075529594653175555) {
   out_9075529594653175555[0] = state[3];
   out_9075529594653175555[1] = state[4];
   out_9075529594653175555[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4668703444104230878) {
   out_4668703444104230878[0] = 0;
   out_4668703444104230878[1] = 0;
   out_4668703444104230878[2] = 0;
   out_4668703444104230878[3] = 1;
   out_4668703444104230878[4] = 0;
   out_4668703444104230878[5] = 0;
   out_4668703444104230878[6] = 0;
   out_4668703444104230878[7] = 0;
   out_4668703444104230878[8] = 0;
   out_4668703444104230878[9] = 0;
   out_4668703444104230878[10] = 0;
   out_4668703444104230878[11] = 0;
   out_4668703444104230878[12] = 0;
   out_4668703444104230878[13] = 0;
   out_4668703444104230878[14] = 0;
   out_4668703444104230878[15] = 0;
   out_4668703444104230878[16] = 0;
   out_4668703444104230878[17] = 0;
   out_4668703444104230878[18] = 0;
   out_4668703444104230878[19] = 0;
   out_4668703444104230878[20] = 0;
   out_4668703444104230878[21] = 0;
   out_4668703444104230878[22] = 1;
   out_4668703444104230878[23] = 0;
   out_4668703444104230878[24] = 0;
   out_4668703444104230878[25] = 0;
   out_4668703444104230878[26] = 0;
   out_4668703444104230878[27] = 0;
   out_4668703444104230878[28] = 0;
   out_4668703444104230878[29] = 0;
   out_4668703444104230878[30] = 0;
   out_4668703444104230878[31] = 0;
   out_4668703444104230878[32] = 0;
   out_4668703444104230878[33] = 0;
   out_4668703444104230878[34] = 0;
   out_4668703444104230878[35] = 0;
   out_4668703444104230878[36] = 0;
   out_4668703444104230878[37] = 0;
   out_4668703444104230878[38] = 0;
   out_4668703444104230878[39] = 0;
   out_4668703444104230878[40] = 0;
   out_4668703444104230878[41] = 1;
   out_4668703444104230878[42] = 0;
   out_4668703444104230878[43] = 0;
   out_4668703444104230878[44] = 0;
   out_4668703444104230878[45] = 0;
   out_4668703444104230878[46] = 0;
   out_4668703444104230878[47] = 0;
   out_4668703444104230878[48] = 0;
   out_4668703444104230878[49] = 0;
   out_4668703444104230878[50] = 0;
   out_4668703444104230878[51] = 0;
   out_4668703444104230878[52] = 0;
   out_4668703444104230878[53] = 0;
}
void h_14(double *state, double *unused, double *out_6684644170062039646) {
   out_6684644170062039646[0] = state[6];
   out_6684644170062039646[1] = state[7];
   out_6684644170062039646[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3917736413097079150) {
   out_3917736413097079150[0] = 0;
   out_3917736413097079150[1] = 0;
   out_3917736413097079150[2] = 0;
   out_3917736413097079150[3] = 0;
   out_3917736413097079150[4] = 0;
   out_3917736413097079150[5] = 0;
   out_3917736413097079150[6] = 1;
   out_3917736413097079150[7] = 0;
   out_3917736413097079150[8] = 0;
   out_3917736413097079150[9] = 0;
   out_3917736413097079150[10] = 0;
   out_3917736413097079150[11] = 0;
   out_3917736413097079150[12] = 0;
   out_3917736413097079150[13] = 0;
   out_3917736413097079150[14] = 0;
   out_3917736413097079150[15] = 0;
   out_3917736413097079150[16] = 0;
   out_3917736413097079150[17] = 0;
   out_3917736413097079150[18] = 0;
   out_3917736413097079150[19] = 0;
   out_3917736413097079150[20] = 0;
   out_3917736413097079150[21] = 0;
   out_3917736413097079150[22] = 0;
   out_3917736413097079150[23] = 0;
   out_3917736413097079150[24] = 0;
   out_3917736413097079150[25] = 1;
   out_3917736413097079150[26] = 0;
   out_3917736413097079150[27] = 0;
   out_3917736413097079150[28] = 0;
   out_3917736413097079150[29] = 0;
   out_3917736413097079150[30] = 0;
   out_3917736413097079150[31] = 0;
   out_3917736413097079150[32] = 0;
   out_3917736413097079150[33] = 0;
   out_3917736413097079150[34] = 0;
   out_3917736413097079150[35] = 0;
   out_3917736413097079150[36] = 0;
   out_3917736413097079150[37] = 0;
   out_3917736413097079150[38] = 0;
   out_3917736413097079150[39] = 0;
   out_3917736413097079150[40] = 0;
   out_3917736413097079150[41] = 0;
   out_3917736413097079150[42] = 0;
   out_3917736413097079150[43] = 0;
   out_3917736413097079150[44] = 1;
   out_3917736413097079150[45] = 0;
   out_3917736413097079150[46] = 0;
   out_3917736413097079150[47] = 0;
   out_3917736413097079150[48] = 0;
   out_3917736413097079150[49] = 0;
   out_3917736413097079150[50] = 0;
   out_3917736413097079150[51] = 0;
   out_3917736413097079150[52] = 0;
   out_3917736413097079150[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5143015347590812681) {
  err_fun(nom_x, delta_x, out_5143015347590812681);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1498290725825032559) {
  inv_err_fun(nom_x, true_x, out_1498290725825032559);
}
void pose_H_mod_fun(double *state, double *out_4606755190645614426) {
  H_mod_fun(state, out_4606755190645614426);
}
void pose_f_fun(double *state, double dt, double *out_8576950781836710085) {
  f_fun(state,  dt, out_8576950781836710085);
}
void pose_F_fun(double *state, double dt, double *out_9071365926554278405) {
  F_fun(state,  dt, out_9071365926554278405);
}
void pose_h_4(double *state, double *unused, double *out_7694457163636602289) {
  h_4(state, unused, out_7694457163636602289);
}
void pose_H_4(double *state, double *unused, double *out_7880977269436563679) {
  H_4(state, unused, out_7880977269436563679);
}
void pose_h_10(double *state, double *unused, double *out_5236443719394936462) {
  h_10(state, unused, out_5236443719394936462);
}
void pose_H_10(double *state, double *unused, double *out_8689295297570059510) {
  H_10(state, unused, out_8689295297570059510);
}
void pose_h_13(double *state, double *unused, double *out_9075529594653175555) {
  h_13(state, unused, out_9075529594653175555);
}
void pose_H_13(double *state, double *unused, double *out_4668703444104230878) {
  H_13(state, unused, out_4668703444104230878);
}
void pose_h_14(double *state, double *unused, double *out_6684644170062039646) {
  h_14(state, unused, out_6684644170062039646);
}
void pose_H_14(double *state, double *unused, double *out_3917736413097079150) {
  H_14(state, unused, out_3917736413097079150);
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
