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
void err_fun(double *nom_x, double *delta_x, double *out_6507930050433723456) {
   out_6507930050433723456[0] = delta_x[0] + nom_x[0];
   out_6507930050433723456[1] = delta_x[1] + nom_x[1];
   out_6507930050433723456[2] = delta_x[2] + nom_x[2];
   out_6507930050433723456[3] = delta_x[3] + nom_x[3];
   out_6507930050433723456[4] = delta_x[4] + nom_x[4];
   out_6507930050433723456[5] = delta_x[5] + nom_x[5];
   out_6507930050433723456[6] = delta_x[6] + nom_x[6];
   out_6507930050433723456[7] = delta_x[7] + nom_x[7];
   out_6507930050433723456[8] = delta_x[8] + nom_x[8];
   out_6507930050433723456[9] = delta_x[9] + nom_x[9];
   out_6507930050433723456[10] = delta_x[10] + nom_x[10];
   out_6507930050433723456[11] = delta_x[11] + nom_x[11];
   out_6507930050433723456[12] = delta_x[12] + nom_x[12];
   out_6507930050433723456[13] = delta_x[13] + nom_x[13];
   out_6507930050433723456[14] = delta_x[14] + nom_x[14];
   out_6507930050433723456[15] = delta_x[15] + nom_x[15];
   out_6507930050433723456[16] = delta_x[16] + nom_x[16];
   out_6507930050433723456[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4828699442560272840) {
   out_4828699442560272840[0] = -nom_x[0] + true_x[0];
   out_4828699442560272840[1] = -nom_x[1] + true_x[1];
   out_4828699442560272840[2] = -nom_x[2] + true_x[2];
   out_4828699442560272840[3] = -nom_x[3] + true_x[3];
   out_4828699442560272840[4] = -nom_x[4] + true_x[4];
   out_4828699442560272840[5] = -nom_x[5] + true_x[5];
   out_4828699442560272840[6] = -nom_x[6] + true_x[6];
   out_4828699442560272840[7] = -nom_x[7] + true_x[7];
   out_4828699442560272840[8] = -nom_x[8] + true_x[8];
   out_4828699442560272840[9] = -nom_x[9] + true_x[9];
   out_4828699442560272840[10] = -nom_x[10] + true_x[10];
   out_4828699442560272840[11] = -nom_x[11] + true_x[11];
   out_4828699442560272840[12] = -nom_x[12] + true_x[12];
   out_4828699442560272840[13] = -nom_x[13] + true_x[13];
   out_4828699442560272840[14] = -nom_x[14] + true_x[14];
   out_4828699442560272840[15] = -nom_x[15] + true_x[15];
   out_4828699442560272840[16] = -nom_x[16] + true_x[16];
   out_4828699442560272840[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6044345162965507958) {
   out_6044345162965507958[0] = 1.0;
   out_6044345162965507958[1] = 0.0;
   out_6044345162965507958[2] = 0.0;
   out_6044345162965507958[3] = 0.0;
   out_6044345162965507958[4] = 0.0;
   out_6044345162965507958[5] = 0.0;
   out_6044345162965507958[6] = 0.0;
   out_6044345162965507958[7] = 0.0;
   out_6044345162965507958[8] = 0.0;
   out_6044345162965507958[9] = 0.0;
   out_6044345162965507958[10] = 0.0;
   out_6044345162965507958[11] = 0.0;
   out_6044345162965507958[12] = 0.0;
   out_6044345162965507958[13] = 0.0;
   out_6044345162965507958[14] = 0.0;
   out_6044345162965507958[15] = 0.0;
   out_6044345162965507958[16] = 0.0;
   out_6044345162965507958[17] = 0.0;
   out_6044345162965507958[18] = 0.0;
   out_6044345162965507958[19] = 1.0;
   out_6044345162965507958[20] = 0.0;
   out_6044345162965507958[21] = 0.0;
   out_6044345162965507958[22] = 0.0;
   out_6044345162965507958[23] = 0.0;
   out_6044345162965507958[24] = 0.0;
   out_6044345162965507958[25] = 0.0;
   out_6044345162965507958[26] = 0.0;
   out_6044345162965507958[27] = 0.0;
   out_6044345162965507958[28] = 0.0;
   out_6044345162965507958[29] = 0.0;
   out_6044345162965507958[30] = 0.0;
   out_6044345162965507958[31] = 0.0;
   out_6044345162965507958[32] = 0.0;
   out_6044345162965507958[33] = 0.0;
   out_6044345162965507958[34] = 0.0;
   out_6044345162965507958[35] = 0.0;
   out_6044345162965507958[36] = 0.0;
   out_6044345162965507958[37] = 0.0;
   out_6044345162965507958[38] = 1.0;
   out_6044345162965507958[39] = 0.0;
   out_6044345162965507958[40] = 0.0;
   out_6044345162965507958[41] = 0.0;
   out_6044345162965507958[42] = 0.0;
   out_6044345162965507958[43] = 0.0;
   out_6044345162965507958[44] = 0.0;
   out_6044345162965507958[45] = 0.0;
   out_6044345162965507958[46] = 0.0;
   out_6044345162965507958[47] = 0.0;
   out_6044345162965507958[48] = 0.0;
   out_6044345162965507958[49] = 0.0;
   out_6044345162965507958[50] = 0.0;
   out_6044345162965507958[51] = 0.0;
   out_6044345162965507958[52] = 0.0;
   out_6044345162965507958[53] = 0.0;
   out_6044345162965507958[54] = 0.0;
   out_6044345162965507958[55] = 0.0;
   out_6044345162965507958[56] = 0.0;
   out_6044345162965507958[57] = 1.0;
   out_6044345162965507958[58] = 0.0;
   out_6044345162965507958[59] = 0.0;
   out_6044345162965507958[60] = 0.0;
   out_6044345162965507958[61] = 0.0;
   out_6044345162965507958[62] = 0.0;
   out_6044345162965507958[63] = 0.0;
   out_6044345162965507958[64] = 0.0;
   out_6044345162965507958[65] = 0.0;
   out_6044345162965507958[66] = 0.0;
   out_6044345162965507958[67] = 0.0;
   out_6044345162965507958[68] = 0.0;
   out_6044345162965507958[69] = 0.0;
   out_6044345162965507958[70] = 0.0;
   out_6044345162965507958[71] = 0.0;
   out_6044345162965507958[72] = 0.0;
   out_6044345162965507958[73] = 0.0;
   out_6044345162965507958[74] = 0.0;
   out_6044345162965507958[75] = 0.0;
   out_6044345162965507958[76] = 1.0;
   out_6044345162965507958[77] = 0.0;
   out_6044345162965507958[78] = 0.0;
   out_6044345162965507958[79] = 0.0;
   out_6044345162965507958[80] = 0.0;
   out_6044345162965507958[81] = 0.0;
   out_6044345162965507958[82] = 0.0;
   out_6044345162965507958[83] = 0.0;
   out_6044345162965507958[84] = 0.0;
   out_6044345162965507958[85] = 0.0;
   out_6044345162965507958[86] = 0.0;
   out_6044345162965507958[87] = 0.0;
   out_6044345162965507958[88] = 0.0;
   out_6044345162965507958[89] = 0.0;
   out_6044345162965507958[90] = 0.0;
   out_6044345162965507958[91] = 0.0;
   out_6044345162965507958[92] = 0.0;
   out_6044345162965507958[93] = 0.0;
   out_6044345162965507958[94] = 0.0;
   out_6044345162965507958[95] = 1.0;
   out_6044345162965507958[96] = 0.0;
   out_6044345162965507958[97] = 0.0;
   out_6044345162965507958[98] = 0.0;
   out_6044345162965507958[99] = 0.0;
   out_6044345162965507958[100] = 0.0;
   out_6044345162965507958[101] = 0.0;
   out_6044345162965507958[102] = 0.0;
   out_6044345162965507958[103] = 0.0;
   out_6044345162965507958[104] = 0.0;
   out_6044345162965507958[105] = 0.0;
   out_6044345162965507958[106] = 0.0;
   out_6044345162965507958[107] = 0.0;
   out_6044345162965507958[108] = 0.0;
   out_6044345162965507958[109] = 0.0;
   out_6044345162965507958[110] = 0.0;
   out_6044345162965507958[111] = 0.0;
   out_6044345162965507958[112] = 0.0;
   out_6044345162965507958[113] = 0.0;
   out_6044345162965507958[114] = 1.0;
   out_6044345162965507958[115] = 0.0;
   out_6044345162965507958[116] = 0.0;
   out_6044345162965507958[117] = 0.0;
   out_6044345162965507958[118] = 0.0;
   out_6044345162965507958[119] = 0.0;
   out_6044345162965507958[120] = 0.0;
   out_6044345162965507958[121] = 0.0;
   out_6044345162965507958[122] = 0.0;
   out_6044345162965507958[123] = 0.0;
   out_6044345162965507958[124] = 0.0;
   out_6044345162965507958[125] = 0.0;
   out_6044345162965507958[126] = 0.0;
   out_6044345162965507958[127] = 0.0;
   out_6044345162965507958[128] = 0.0;
   out_6044345162965507958[129] = 0.0;
   out_6044345162965507958[130] = 0.0;
   out_6044345162965507958[131] = 0.0;
   out_6044345162965507958[132] = 0.0;
   out_6044345162965507958[133] = 1.0;
   out_6044345162965507958[134] = 0.0;
   out_6044345162965507958[135] = 0.0;
   out_6044345162965507958[136] = 0.0;
   out_6044345162965507958[137] = 0.0;
   out_6044345162965507958[138] = 0.0;
   out_6044345162965507958[139] = 0.0;
   out_6044345162965507958[140] = 0.0;
   out_6044345162965507958[141] = 0.0;
   out_6044345162965507958[142] = 0.0;
   out_6044345162965507958[143] = 0.0;
   out_6044345162965507958[144] = 0.0;
   out_6044345162965507958[145] = 0.0;
   out_6044345162965507958[146] = 0.0;
   out_6044345162965507958[147] = 0.0;
   out_6044345162965507958[148] = 0.0;
   out_6044345162965507958[149] = 0.0;
   out_6044345162965507958[150] = 0.0;
   out_6044345162965507958[151] = 0.0;
   out_6044345162965507958[152] = 1.0;
   out_6044345162965507958[153] = 0.0;
   out_6044345162965507958[154] = 0.0;
   out_6044345162965507958[155] = 0.0;
   out_6044345162965507958[156] = 0.0;
   out_6044345162965507958[157] = 0.0;
   out_6044345162965507958[158] = 0.0;
   out_6044345162965507958[159] = 0.0;
   out_6044345162965507958[160] = 0.0;
   out_6044345162965507958[161] = 0.0;
   out_6044345162965507958[162] = 0.0;
   out_6044345162965507958[163] = 0.0;
   out_6044345162965507958[164] = 0.0;
   out_6044345162965507958[165] = 0.0;
   out_6044345162965507958[166] = 0.0;
   out_6044345162965507958[167] = 0.0;
   out_6044345162965507958[168] = 0.0;
   out_6044345162965507958[169] = 0.0;
   out_6044345162965507958[170] = 0.0;
   out_6044345162965507958[171] = 1.0;
   out_6044345162965507958[172] = 0.0;
   out_6044345162965507958[173] = 0.0;
   out_6044345162965507958[174] = 0.0;
   out_6044345162965507958[175] = 0.0;
   out_6044345162965507958[176] = 0.0;
   out_6044345162965507958[177] = 0.0;
   out_6044345162965507958[178] = 0.0;
   out_6044345162965507958[179] = 0.0;
   out_6044345162965507958[180] = 0.0;
   out_6044345162965507958[181] = 0.0;
   out_6044345162965507958[182] = 0.0;
   out_6044345162965507958[183] = 0.0;
   out_6044345162965507958[184] = 0.0;
   out_6044345162965507958[185] = 0.0;
   out_6044345162965507958[186] = 0.0;
   out_6044345162965507958[187] = 0.0;
   out_6044345162965507958[188] = 0.0;
   out_6044345162965507958[189] = 0.0;
   out_6044345162965507958[190] = 1.0;
   out_6044345162965507958[191] = 0.0;
   out_6044345162965507958[192] = 0.0;
   out_6044345162965507958[193] = 0.0;
   out_6044345162965507958[194] = 0.0;
   out_6044345162965507958[195] = 0.0;
   out_6044345162965507958[196] = 0.0;
   out_6044345162965507958[197] = 0.0;
   out_6044345162965507958[198] = 0.0;
   out_6044345162965507958[199] = 0.0;
   out_6044345162965507958[200] = 0.0;
   out_6044345162965507958[201] = 0.0;
   out_6044345162965507958[202] = 0.0;
   out_6044345162965507958[203] = 0.0;
   out_6044345162965507958[204] = 0.0;
   out_6044345162965507958[205] = 0.0;
   out_6044345162965507958[206] = 0.0;
   out_6044345162965507958[207] = 0.0;
   out_6044345162965507958[208] = 0.0;
   out_6044345162965507958[209] = 1.0;
   out_6044345162965507958[210] = 0.0;
   out_6044345162965507958[211] = 0.0;
   out_6044345162965507958[212] = 0.0;
   out_6044345162965507958[213] = 0.0;
   out_6044345162965507958[214] = 0.0;
   out_6044345162965507958[215] = 0.0;
   out_6044345162965507958[216] = 0.0;
   out_6044345162965507958[217] = 0.0;
   out_6044345162965507958[218] = 0.0;
   out_6044345162965507958[219] = 0.0;
   out_6044345162965507958[220] = 0.0;
   out_6044345162965507958[221] = 0.0;
   out_6044345162965507958[222] = 0.0;
   out_6044345162965507958[223] = 0.0;
   out_6044345162965507958[224] = 0.0;
   out_6044345162965507958[225] = 0.0;
   out_6044345162965507958[226] = 0.0;
   out_6044345162965507958[227] = 0.0;
   out_6044345162965507958[228] = 1.0;
   out_6044345162965507958[229] = 0.0;
   out_6044345162965507958[230] = 0.0;
   out_6044345162965507958[231] = 0.0;
   out_6044345162965507958[232] = 0.0;
   out_6044345162965507958[233] = 0.0;
   out_6044345162965507958[234] = 0.0;
   out_6044345162965507958[235] = 0.0;
   out_6044345162965507958[236] = 0.0;
   out_6044345162965507958[237] = 0.0;
   out_6044345162965507958[238] = 0.0;
   out_6044345162965507958[239] = 0.0;
   out_6044345162965507958[240] = 0.0;
   out_6044345162965507958[241] = 0.0;
   out_6044345162965507958[242] = 0.0;
   out_6044345162965507958[243] = 0.0;
   out_6044345162965507958[244] = 0.0;
   out_6044345162965507958[245] = 0.0;
   out_6044345162965507958[246] = 0.0;
   out_6044345162965507958[247] = 1.0;
   out_6044345162965507958[248] = 0.0;
   out_6044345162965507958[249] = 0.0;
   out_6044345162965507958[250] = 0.0;
   out_6044345162965507958[251] = 0.0;
   out_6044345162965507958[252] = 0.0;
   out_6044345162965507958[253] = 0.0;
   out_6044345162965507958[254] = 0.0;
   out_6044345162965507958[255] = 0.0;
   out_6044345162965507958[256] = 0.0;
   out_6044345162965507958[257] = 0.0;
   out_6044345162965507958[258] = 0.0;
   out_6044345162965507958[259] = 0.0;
   out_6044345162965507958[260] = 0.0;
   out_6044345162965507958[261] = 0.0;
   out_6044345162965507958[262] = 0.0;
   out_6044345162965507958[263] = 0.0;
   out_6044345162965507958[264] = 0.0;
   out_6044345162965507958[265] = 0.0;
   out_6044345162965507958[266] = 1.0;
   out_6044345162965507958[267] = 0.0;
   out_6044345162965507958[268] = 0.0;
   out_6044345162965507958[269] = 0.0;
   out_6044345162965507958[270] = 0.0;
   out_6044345162965507958[271] = 0.0;
   out_6044345162965507958[272] = 0.0;
   out_6044345162965507958[273] = 0.0;
   out_6044345162965507958[274] = 0.0;
   out_6044345162965507958[275] = 0.0;
   out_6044345162965507958[276] = 0.0;
   out_6044345162965507958[277] = 0.0;
   out_6044345162965507958[278] = 0.0;
   out_6044345162965507958[279] = 0.0;
   out_6044345162965507958[280] = 0.0;
   out_6044345162965507958[281] = 0.0;
   out_6044345162965507958[282] = 0.0;
   out_6044345162965507958[283] = 0.0;
   out_6044345162965507958[284] = 0.0;
   out_6044345162965507958[285] = 1.0;
   out_6044345162965507958[286] = 0.0;
   out_6044345162965507958[287] = 0.0;
   out_6044345162965507958[288] = 0.0;
   out_6044345162965507958[289] = 0.0;
   out_6044345162965507958[290] = 0.0;
   out_6044345162965507958[291] = 0.0;
   out_6044345162965507958[292] = 0.0;
   out_6044345162965507958[293] = 0.0;
   out_6044345162965507958[294] = 0.0;
   out_6044345162965507958[295] = 0.0;
   out_6044345162965507958[296] = 0.0;
   out_6044345162965507958[297] = 0.0;
   out_6044345162965507958[298] = 0.0;
   out_6044345162965507958[299] = 0.0;
   out_6044345162965507958[300] = 0.0;
   out_6044345162965507958[301] = 0.0;
   out_6044345162965507958[302] = 0.0;
   out_6044345162965507958[303] = 0.0;
   out_6044345162965507958[304] = 1.0;
   out_6044345162965507958[305] = 0.0;
   out_6044345162965507958[306] = 0.0;
   out_6044345162965507958[307] = 0.0;
   out_6044345162965507958[308] = 0.0;
   out_6044345162965507958[309] = 0.0;
   out_6044345162965507958[310] = 0.0;
   out_6044345162965507958[311] = 0.0;
   out_6044345162965507958[312] = 0.0;
   out_6044345162965507958[313] = 0.0;
   out_6044345162965507958[314] = 0.0;
   out_6044345162965507958[315] = 0.0;
   out_6044345162965507958[316] = 0.0;
   out_6044345162965507958[317] = 0.0;
   out_6044345162965507958[318] = 0.0;
   out_6044345162965507958[319] = 0.0;
   out_6044345162965507958[320] = 0.0;
   out_6044345162965507958[321] = 0.0;
   out_6044345162965507958[322] = 0.0;
   out_6044345162965507958[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_2707422486897363634) {
   out_2707422486897363634[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_2707422486897363634[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_2707422486897363634[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_2707422486897363634[3] = dt*state[12] + state[3];
   out_2707422486897363634[4] = dt*state[13] + state[4];
   out_2707422486897363634[5] = dt*state[14] + state[5];
   out_2707422486897363634[6] = state[6];
   out_2707422486897363634[7] = state[7];
   out_2707422486897363634[8] = state[8];
   out_2707422486897363634[9] = state[9];
   out_2707422486897363634[10] = state[10];
   out_2707422486897363634[11] = state[11];
   out_2707422486897363634[12] = state[12];
   out_2707422486897363634[13] = state[13];
   out_2707422486897363634[14] = state[14];
   out_2707422486897363634[15] = state[15];
   out_2707422486897363634[16] = state[16];
   out_2707422486897363634[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2783420399776033045) {
   out_2783420399776033045[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2783420399776033045[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2783420399776033045[2] = 0;
   out_2783420399776033045[3] = 0;
   out_2783420399776033045[4] = 0;
   out_2783420399776033045[5] = 0;
   out_2783420399776033045[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2783420399776033045[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2783420399776033045[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2783420399776033045[9] = 0;
   out_2783420399776033045[10] = 0;
   out_2783420399776033045[11] = 0;
   out_2783420399776033045[12] = 0;
   out_2783420399776033045[13] = 0;
   out_2783420399776033045[14] = 0;
   out_2783420399776033045[15] = 0;
   out_2783420399776033045[16] = 0;
   out_2783420399776033045[17] = 0;
   out_2783420399776033045[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2783420399776033045[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2783420399776033045[20] = 0;
   out_2783420399776033045[21] = 0;
   out_2783420399776033045[22] = 0;
   out_2783420399776033045[23] = 0;
   out_2783420399776033045[24] = 0;
   out_2783420399776033045[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2783420399776033045[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2783420399776033045[27] = 0;
   out_2783420399776033045[28] = 0;
   out_2783420399776033045[29] = 0;
   out_2783420399776033045[30] = 0;
   out_2783420399776033045[31] = 0;
   out_2783420399776033045[32] = 0;
   out_2783420399776033045[33] = 0;
   out_2783420399776033045[34] = 0;
   out_2783420399776033045[35] = 0;
   out_2783420399776033045[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2783420399776033045[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2783420399776033045[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2783420399776033045[39] = 0;
   out_2783420399776033045[40] = 0;
   out_2783420399776033045[41] = 0;
   out_2783420399776033045[42] = 0;
   out_2783420399776033045[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2783420399776033045[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2783420399776033045[45] = 0;
   out_2783420399776033045[46] = 0;
   out_2783420399776033045[47] = 0;
   out_2783420399776033045[48] = 0;
   out_2783420399776033045[49] = 0;
   out_2783420399776033045[50] = 0;
   out_2783420399776033045[51] = 0;
   out_2783420399776033045[52] = 0;
   out_2783420399776033045[53] = 0;
   out_2783420399776033045[54] = 0;
   out_2783420399776033045[55] = 0;
   out_2783420399776033045[56] = 0;
   out_2783420399776033045[57] = 1;
   out_2783420399776033045[58] = 0;
   out_2783420399776033045[59] = 0;
   out_2783420399776033045[60] = 0;
   out_2783420399776033045[61] = 0;
   out_2783420399776033045[62] = 0;
   out_2783420399776033045[63] = 0;
   out_2783420399776033045[64] = 0;
   out_2783420399776033045[65] = 0;
   out_2783420399776033045[66] = dt;
   out_2783420399776033045[67] = 0;
   out_2783420399776033045[68] = 0;
   out_2783420399776033045[69] = 0;
   out_2783420399776033045[70] = 0;
   out_2783420399776033045[71] = 0;
   out_2783420399776033045[72] = 0;
   out_2783420399776033045[73] = 0;
   out_2783420399776033045[74] = 0;
   out_2783420399776033045[75] = 0;
   out_2783420399776033045[76] = 1;
   out_2783420399776033045[77] = 0;
   out_2783420399776033045[78] = 0;
   out_2783420399776033045[79] = 0;
   out_2783420399776033045[80] = 0;
   out_2783420399776033045[81] = 0;
   out_2783420399776033045[82] = 0;
   out_2783420399776033045[83] = 0;
   out_2783420399776033045[84] = 0;
   out_2783420399776033045[85] = dt;
   out_2783420399776033045[86] = 0;
   out_2783420399776033045[87] = 0;
   out_2783420399776033045[88] = 0;
   out_2783420399776033045[89] = 0;
   out_2783420399776033045[90] = 0;
   out_2783420399776033045[91] = 0;
   out_2783420399776033045[92] = 0;
   out_2783420399776033045[93] = 0;
   out_2783420399776033045[94] = 0;
   out_2783420399776033045[95] = 1;
   out_2783420399776033045[96] = 0;
   out_2783420399776033045[97] = 0;
   out_2783420399776033045[98] = 0;
   out_2783420399776033045[99] = 0;
   out_2783420399776033045[100] = 0;
   out_2783420399776033045[101] = 0;
   out_2783420399776033045[102] = 0;
   out_2783420399776033045[103] = 0;
   out_2783420399776033045[104] = dt;
   out_2783420399776033045[105] = 0;
   out_2783420399776033045[106] = 0;
   out_2783420399776033045[107] = 0;
   out_2783420399776033045[108] = 0;
   out_2783420399776033045[109] = 0;
   out_2783420399776033045[110] = 0;
   out_2783420399776033045[111] = 0;
   out_2783420399776033045[112] = 0;
   out_2783420399776033045[113] = 0;
   out_2783420399776033045[114] = 1;
   out_2783420399776033045[115] = 0;
   out_2783420399776033045[116] = 0;
   out_2783420399776033045[117] = 0;
   out_2783420399776033045[118] = 0;
   out_2783420399776033045[119] = 0;
   out_2783420399776033045[120] = 0;
   out_2783420399776033045[121] = 0;
   out_2783420399776033045[122] = 0;
   out_2783420399776033045[123] = 0;
   out_2783420399776033045[124] = 0;
   out_2783420399776033045[125] = 0;
   out_2783420399776033045[126] = 0;
   out_2783420399776033045[127] = 0;
   out_2783420399776033045[128] = 0;
   out_2783420399776033045[129] = 0;
   out_2783420399776033045[130] = 0;
   out_2783420399776033045[131] = 0;
   out_2783420399776033045[132] = 0;
   out_2783420399776033045[133] = 1;
   out_2783420399776033045[134] = 0;
   out_2783420399776033045[135] = 0;
   out_2783420399776033045[136] = 0;
   out_2783420399776033045[137] = 0;
   out_2783420399776033045[138] = 0;
   out_2783420399776033045[139] = 0;
   out_2783420399776033045[140] = 0;
   out_2783420399776033045[141] = 0;
   out_2783420399776033045[142] = 0;
   out_2783420399776033045[143] = 0;
   out_2783420399776033045[144] = 0;
   out_2783420399776033045[145] = 0;
   out_2783420399776033045[146] = 0;
   out_2783420399776033045[147] = 0;
   out_2783420399776033045[148] = 0;
   out_2783420399776033045[149] = 0;
   out_2783420399776033045[150] = 0;
   out_2783420399776033045[151] = 0;
   out_2783420399776033045[152] = 1;
   out_2783420399776033045[153] = 0;
   out_2783420399776033045[154] = 0;
   out_2783420399776033045[155] = 0;
   out_2783420399776033045[156] = 0;
   out_2783420399776033045[157] = 0;
   out_2783420399776033045[158] = 0;
   out_2783420399776033045[159] = 0;
   out_2783420399776033045[160] = 0;
   out_2783420399776033045[161] = 0;
   out_2783420399776033045[162] = 0;
   out_2783420399776033045[163] = 0;
   out_2783420399776033045[164] = 0;
   out_2783420399776033045[165] = 0;
   out_2783420399776033045[166] = 0;
   out_2783420399776033045[167] = 0;
   out_2783420399776033045[168] = 0;
   out_2783420399776033045[169] = 0;
   out_2783420399776033045[170] = 0;
   out_2783420399776033045[171] = 1;
   out_2783420399776033045[172] = 0;
   out_2783420399776033045[173] = 0;
   out_2783420399776033045[174] = 0;
   out_2783420399776033045[175] = 0;
   out_2783420399776033045[176] = 0;
   out_2783420399776033045[177] = 0;
   out_2783420399776033045[178] = 0;
   out_2783420399776033045[179] = 0;
   out_2783420399776033045[180] = 0;
   out_2783420399776033045[181] = 0;
   out_2783420399776033045[182] = 0;
   out_2783420399776033045[183] = 0;
   out_2783420399776033045[184] = 0;
   out_2783420399776033045[185] = 0;
   out_2783420399776033045[186] = 0;
   out_2783420399776033045[187] = 0;
   out_2783420399776033045[188] = 0;
   out_2783420399776033045[189] = 0;
   out_2783420399776033045[190] = 1;
   out_2783420399776033045[191] = 0;
   out_2783420399776033045[192] = 0;
   out_2783420399776033045[193] = 0;
   out_2783420399776033045[194] = 0;
   out_2783420399776033045[195] = 0;
   out_2783420399776033045[196] = 0;
   out_2783420399776033045[197] = 0;
   out_2783420399776033045[198] = 0;
   out_2783420399776033045[199] = 0;
   out_2783420399776033045[200] = 0;
   out_2783420399776033045[201] = 0;
   out_2783420399776033045[202] = 0;
   out_2783420399776033045[203] = 0;
   out_2783420399776033045[204] = 0;
   out_2783420399776033045[205] = 0;
   out_2783420399776033045[206] = 0;
   out_2783420399776033045[207] = 0;
   out_2783420399776033045[208] = 0;
   out_2783420399776033045[209] = 1;
   out_2783420399776033045[210] = 0;
   out_2783420399776033045[211] = 0;
   out_2783420399776033045[212] = 0;
   out_2783420399776033045[213] = 0;
   out_2783420399776033045[214] = 0;
   out_2783420399776033045[215] = 0;
   out_2783420399776033045[216] = 0;
   out_2783420399776033045[217] = 0;
   out_2783420399776033045[218] = 0;
   out_2783420399776033045[219] = 0;
   out_2783420399776033045[220] = 0;
   out_2783420399776033045[221] = 0;
   out_2783420399776033045[222] = 0;
   out_2783420399776033045[223] = 0;
   out_2783420399776033045[224] = 0;
   out_2783420399776033045[225] = 0;
   out_2783420399776033045[226] = 0;
   out_2783420399776033045[227] = 0;
   out_2783420399776033045[228] = 1;
   out_2783420399776033045[229] = 0;
   out_2783420399776033045[230] = 0;
   out_2783420399776033045[231] = 0;
   out_2783420399776033045[232] = 0;
   out_2783420399776033045[233] = 0;
   out_2783420399776033045[234] = 0;
   out_2783420399776033045[235] = 0;
   out_2783420399776033045[236] = 0;
   out_2783420399776033045[237] = 0;
   out_2783420399776033045[238] = 0;
   out_2783420399776033045[239] = 0;
   out_2783420399776033045[240] = 0;
   out_2783420399776033045[241] = 0;
   out_2783420399776033045[242] = 0;
   out_2783420399776033045[243] = 0;
   out_2783420399776033045[244] = 0;
   out_2783420399776033045[245] = 0;
   out_2783420399776033045[246] = 0;
   out_2783420399776033045[247] = 1;
   out_2783420399776033045[248] = 0;
   out_2783420399776033045[249] = 0;
   out_2783420399776033045[250] = 0;
   out_2783420399776033045[251] = 0;
   out_2783420399776033045[252] = 0;
   out_2783420399776033045[253] = 0;
   out_2783420399776033045[254] = 0;
   out_2783420399776033045[255] = 0;
   out_2783420399776033045[256] = 0;
   out_2783420399776033045[257] = 0;
   out_2783420399776033045[258] = 0;
   out_2783420399776033045[259] = 0;
   out_2783420399776033045[260] = 0;
   out_2783420399776033045[261] = 0;
   out_2783420399776033045[262] = 0;
   out_2783420399776033045[263] = 0;
   out_2783420399776033045[264] = 0;
   out_2783420399776033045[265] = 0;
   out_2783420399776033045[266] = 1;
   out_2783420399776033045[267] = 0;
   out_2783420399776033045[268] = 0;
   out_2783420399776033045[269] = 0;
   out_2783420399776033045[270] = 0;
   out_2783420399776033045[271] = 0;
   out_2783420399776033045[272] = 0;
   out_2783420399776033045[273] = 0;
   out_2783420399776033045[274] = 0;
   out_2783420399776033045[275] = 0;
   out_2783420399776033045[276] = 0;
   out_2783420399776033045[277] = 0;
   out_2783420399776033045[278] = 0;
   out_2783420399776033045[279] = 0;
   out_2783420399776033045[280] = 0;
   out_2783420399776033045[281] = 0;
   out_2783420399776033045[282] = 0;
   out_2783420399776033045[283] = 0;
   out_2783420399776033045[284] = 0;
   out_2783420399776033045[285] = 1;
   out_2783420399776033045[286] = 0;
   out_2783420399776033045[287] = 0;
   out_2783420399776033045[288] = 0;
   out_2783420399776033045[289] = 0;
   out_2783420399776033045[290] = 0;
   out_2783420399776033045[291] = 0;
   out_2783420399776033045[292] = 0;
   out_2783420399776033045[293] = 0;
   out_2783420399776033045[294] = 0;
   out_2783420399776033045[295] = 0;
   out_2783420399776033045[296] = 0;
   out_2783420399776033045[297] = 0;
   out_2783420399776033045[298] = 0;
   out_2783420399776033045[299] = 0;
   out_2783420399776033045[300] = 0;
   out_2783420399776033045[301] = 0;
   out_2783420399776033045[302] = 0;
   out_2783420399776033045[303] = 0;
   out_2783420399776033045[304] = 1;
   out_2783420399776033045[305] = 0;
   out_2783420399776033045[306] = 0;
   out_2783420399776033045[307] = 0;
   out_2783420399776033045[308] = 0;
   out_2783420399776033045[309] = 0;
   out_2783420399776033045[310] = 0;
   out_2783420399776033045[311] = 0;
   out_2783420399776033045[312] = 0;
   out_2783420399776033045[313] = 0;
   out_2783420399776033045[314] = 0;
   out_2783420399776033045[315] = 0;
   out_2783420399776033045[316] = 0;
   out_2783420399776033045[317] = 0;
   out_2783420399776033045[318] = 0;
   out_2783420399776033045[319] = 0;
   out_2783420399776033045[320] = 0;
   out_2783420399776033045[321] = 0;
   out_2783420399776033045[322] = 0;
   out_2783420399776033045[323] = 1;
}
void h_4(double *state, double *unused, double *out_6625322830489649201) {
   out_6625322830489649201[0] = state[6] + state[9];
   out_6625322830489649201[1] = state[7] + state[10];
   out_6625322830489649201[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_891826777926427223) {
   out_891826777926427223[0] = 0;
   out_891826777926427223[1] = 0;
   out_891826777926427223[2] = 0;
   out_891826777926427223[3] = 0;
   out_891826777926427223[4] = 0;
   out_891826777926427223[5] = 0;
   out_891826777926427223[6] = 1;
   out_891826777926427223[7] = 0;
   out_891826777926427223[8] = 0;
   out_891826777926427223[9] = 1;
   out_891826777926427223[10] = 0;
   out_891826777926427223[11] = 0;
   out_891826777926427223[12] = 0;
   out_891826777926427223[13] = 0;
   out_891826777926427223[14] = 0;
   out_891826777926427223[15] = 0;
   out_891826777926427223[16] = 0;
   out_891826777926427223[17] = 0;
   out_891826777926427223[18] = 0;
   out_891826777926427223[19] = 0;
   out_891826777926427223[20] = 0;
   out_891826777926427223[21] = 0;
   out_891826777926427223[22] = 0;
   out_891826777926427223[23] = 0;
   out_891826777926427223[24] = 0;
   out_891826777926427223[25] = 1;
   out_891826777926427223[26] = 0;
   out_891826777926427223[27] = 0;
   out_891826777926427223[28] = 1;
   out_891826777926427223[29] = 0;
   out_891826777926427223[30] = 0;
   out_891826777926427223[31] = 0;
   out_891826777926427223[32] = 0;
   out_891826777926427223[33] = 0;
   out_891826777926427223[34] = 0;
   out_891826777926427223[35] = 0;
   out_891826777926427223[36] = 0;
   out_891826777926427223[37] = 0;
   out_891826777926427223[38] = 0;
   out_891826777926427223[39] = 0;
   out_891826777926427223[40] = 0;
   out_891826777926427223[41] = 0;
   out_891826777926427223[42] = 0;
   out_891826777926427223[43] = 0;
   out_891826777926427223[44] = 1;
   out_891826777926427223[45] = 0;
   out_891826777926427223[46] = 0;
   out_891826777926427223[47] = 1;
   out_891826777926427223[48] = 0;
   out_891826777926427223[49] = 0;
   out_891826777926427223[50] = 0;
   out_891826777926427223[51] = 0;
   out_891826777926427223[52] = 0;
   out_891826777926427223[53] = 0;
}
void h_10(double *state, double *unused, double *out_495585793918053605) {
   out_495585793918053605[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_495585793918053605[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_495585793918053605[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8682725662931185277) {
   out_8682725662931185277[0] = 0;
   out_8682725662931185277[1] = 9.8100000000000005*cos(state[1]);
   out_8682725662931185277[2] = 0;
   out_8682725662931185277[3] = 0;
   out_8682725662931185277[4] = -state[8];
   out_8682725662931185277[5] = state[7];
   out_8682725662931185277[6] = 0;
   out_8682725662931185277[7] = state[5];
   out_8682725662931185277[8] = -state[4];
   out_8682725662931185277[9] = 0;
   out_8682725662931185277[10] = 0;
   out_8682725662931185277[11] = 0;
   out_8682725662931185277[12] = 1;
   out_8682725662931185277[13] = 0;
   out_8682725662931185277[14] = 0;
   out_8682725662931185277[15] = 1;
   out_8682725662931185277[16] = 0;
   out_8682725662931185277[17] = 0;
   out_8682725662931185277[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8682725662931185277[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8682725662931185277[20] = 0;
   out_8682725662931185277[21] = state[8];
   out_8682725662931185277[22] = 0;
   out_8682725662931185277[23] = -state[6];
   out_8682725662931185277[24] = -state[5];
   out_8682725662931185277[25] = 0;
   out_8682725662931185277[26] = state[3];
   out_8682725662931185277[27] = 0;
   out_8682725662931185277[28] = 0;
   out_8682725662931185277[29] = 0;
   out_8682725662931185277[30] = 0;
   out_8682725662931185277[31] = 1;
   out_8682725662931185277[32] = 0;
   out_8682725662931185277[33] = 0;
   out_8682725662931185277[34] = 1;
   out_8682725662931185277[35] = 0;
   out_8682725662931185277[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8682725662931185277[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8682725662931185277[38] = 0;
   out_8682725662931185277[39] = -state[7];
   out_8682725662931185277[40] = state[6];
   out_8682725662931185277[41] = 0;
   out_8682725662931185277[42] = state[4];
   out_8682725662931185277[43] = -state[3];
   out_8682725662931185277[44] = 0;
   out_8682725662931185277[45] = 0;
   out_8682725662931185277[46] = 0;
   out_8682725662931185277[47] = 0;
   out_8682725662931185277[48] = 0;
   out_8682725662931185277[49] = 0;
   out_8682725662931185277[50] = 1;
   out_8682725662931185277[51] = 0;
   out_8682725662931185277[52] = 0;
   out_8682725662931185277[53] = 1;
}
void h_13(double *state, double *unused, double *out_6437595282912769194) {
   out_6437595282912769194[0] = state[3];
   out_6437595282912769194[1] = state[4];
   out_6437595282912769194[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2320447047405905578) {
   out_2320447047405905578[0] = 0;
   out_2320447047405905578[1] = 0;
   out_2320447047405905578[2] = 0;
   out_2320447047405905578[3] = 1;
   out_2320447047405905578[4] = 0;
   out_2320447047405905578[5] = 0;
   out_2320447047405905578[6] = 0;
   out_2320447047405905578[7] = 0;
   out_2320447047405905578[8] = 0;
   out_2320447047405905578[9] = 0;
   out_2320447047405905578[10] = 0;
   out_2320447047405905578[11] = 0;
   out_2320447047405905578[12] = 0;
   out_2320447047405905578[13] = 0;
   out_2320447047405905578[14] = 0;
   out_2320447047405905578[15] = 0;
   out_2320447047405905578[16] = 0;
   out_2320447047405905578[17] = 0;
   out_2320447047405905578[18] = 0;
   out_2320447047405905578[19] = 0;
   out_2320447047405905578[20] = 0;
   out_2320447047405905578[21] = 0;
   out_2320447047405905578[22] = 1;
   out_2320447047405905578[23] = 0;
   out_2320447047405905578[24] = 0;
   out_2320447047405905578[25] = 0;
   out_2320447047405905578[26] = 0;
   out_2320447047405905578[27] = 0;
   out_2320447047405905578[28] = 0;
   out_2320447047405905578[29] = 0;
   out_2320447047405905578[30] = 0;
   out_2320447047405905578[31] = 0;
   out_2320447047405905578[32] = 0;
   out_2320447047405905578[33] = 0;
   out_2320447047405905578[34] = 0;
   out_2320447047405905578[35] = 0;
   out_2320447047405905578[36] = 0;
   out_2320447047405905578[37] = 0;
   out_2320447047405905578[38] = 0;
   out_2320447047405905578[39] = 0;
   out_2320447047405905578[40] = 0;
   out_2320447047405905578[41] = 1;
   out_2320447047405905578[42] = 0;
   out_2320447047405905578[43] = 0;
   out_2320447047405905578[44] = 0;
   out_2320447047405905578[45] = 0;
   out_2320447047405905578[46] = 0;
   out_2320447047405905578[47] = 0;
   out_2320447047405905578[48] = 0;
   out_2320447047405905578[49] = 0;
   out_2320447047405905578[50] = 0;
   out_2320447047405905578[51] = 0;
   out_2320447047405905578[52] = 0;
   out_2320447047405905578[53] = 0;
}
void h_14(double *state, double *unused, double *out_1731855561045144303) {
   out_1731855561045144303[0] = state[6];
   out_1731855561045144303[1] = state[7];
   out_1731855561045144303[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1326943304571310822) {
   out_1326943304571310822[0] = 0;
   out_1326943304571310822[1] = 0;
   out_1326943304571310822[2] = 0;
   out_1326943304571310822[3] = 0;
   out_1326943304571310822[4] = 0;
   out_1326943304571310822[5] = 0;
   out_1326943304571310822[6] = 1;
   out_1326943304571310822[7] = 0;
   out_1326943304571310822[8] = 0;
   out_1326943304571310822[9] = 0;
   out_1326943304571310822[10] = 0;
   out_1326943304571310822[11] = 0;
   out_1326943304571310822[12] = 0;
   out_1326943304571310822[13] = 0;
   out_1326943304571310822[14] = 0;
   out_1326943304571310822[15] = 0;
   out_1326943304571310822[16] = 0;
   out_1326943304571310822[17] = 0;
   out_1326943304571310822[18] = 0;
   out_1326943304571310822[19] = 0;
   out_1326943304571310822[20] = 0;
   out_1326943304571310822[21] = 0;
   out_1326943304571310822[22] = 0;
   out_1326943304571310822[23] = 0;
   out_1326943304571310822[24] = 0;
   out_1326943304571310822[25] = 1;
   out_1326943304571310822[26] = 0;
   out_1326943304571310822[27] = 0;
   out_1326943304571310822[28] = 0;
   out_1326943304571310822[29] = 0;
   out_1326943304571310822[30] = 0;
   out_1326943304571310822[31] = 0;
   out_1326943304571310822[32] = 0;
   out_1326943304571310822[33] = 0;
   out_1326943304571310822[34] = 0;
   out_1326943304571310822[35] = 0;
   out_1326943304571310822[36] = 0;
   out_1326943304571310822[37] = 0;
   out_1326943304571310822[38] = 0;
   out_1326943304571310822[39] = 0;
   out_1326943304571310822[40] = 0;
   out_1326943304571310822[41] = 0;
   out_1326943304571310822[42] = 0;
   out_1326943304571310822[43] = 0;
   out_1326943304571310822[44] = 1;
   out_1326943304571310822[45] = 0;
   out_1326943304571310822[46] = 0;
   out_1326943304571310822[47] = 0;
   out_1326943304571310822[48] = 0;
   out_1326943304571310822[49] = 0;
   out_1326943304571310822[50] = 0;
   out_1326943304571310822[51] = 0;
   out_1326943304571310822[52] = 0;
   out_1326943304571310822[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_6507930050433723456) {
  err_fun(nom_x, delta_x, out_6507930050433723456);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4828699442560272840) {
  inv_err_fun(nom_x, true_x, out_4828699442560272840);
}
void pose_H_mod_fun(double *state, double *out_6044345162965507958) {
  H_mod_fun(state, out_6044345162965507958);
}
void pose_f_fun(double *state, double dt, double *out_2707422486897363634) {
  f_fun(state,  dt, out_2707422486897363634);
}
void pose_F_fun(double *state, double dt, double *out_2783420399776033045) {
  F_fun(state,  dt, out_2783420399776033045);
}
void pose_h_4(double *state, double *unused, double *out_6625322830489649201) {
  h_4(state, unused, out_6625322830489649201);
}
void pose_H_4(double *state, double *unused, double *out_891826777926427223) {
  H_4(state, unused, out_891826777926427223);
}
void pose_h_10(double *state, double *unused, double *out_495585793918053605) {
  h_10(state, unused, out_495585793918053605);
}
void pose_H_10(double *state, double *unused, double *out_8682725662931185277) {
  H_10(state, unused, out_8682725662931185277);
}
void pose_h_13(double *state, double *unused, double *out_6437595282912769194) {
  h_13(state, unused, out_6437595282912769194);
}
void pose_H_13(double *state, double *unused, double *out_2320447047405905578) {
  H_13(state, unused, out_2320447047405905578);
}
void pose_h_14(double *state, double *unused, double *out_1731855561045144303) {
  h_14(state, unused, out_1731855561045144303);
}
void pose_H_14(double *state, double *unused, double *out_1326943304571310822) {
  H_14(state, unused, out_1326943304571310822);
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
