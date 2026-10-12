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
void err_fun(double *nom_x, double *delta_x, double *out_4948547112888214127) {
   out_4948547112888214127[0] = delta_x[0] + nom_x[0];
   out_4948547112888214127[1] = delta_x[1] + nom_x[1];
   out_4948547112888214127[2] = delta_x[2] + nom_x[2];
   out_4948547112888214127[3] = delta_x[3] + nom_x[3];
   out_4948547112888214127[4] = delta_x[4] + nom_x[4];
   out_4948547112888214127[5] = delta_x[5] + nom_x[5];
   out_4948547112888214127[6] = delta_x[6] + nom_x[6];
   out_4948547112888214127[7] = delta_x[7] + nom_x[7];
   out_4948547112888214127[8] = delta_x[8] + nom_x[8];
   out_4948547112888214127[9] = delta_x[9] + nom_x[9];
   out_4948547112888214127[10] = delta_x[10] + nom_x[10];
   out_4948547112888214127[11] = delta_x[11] + nom_x[11];
   out_4948547112888214127[12] = delta_x[12] + nom_x[12];
   out_4948547112888214127[13] = delta_x[13] + nom_x[13];
   out_4948547112888214127[14] = delta_x[14] + nom_x[14];
   out_4948547112888214127[15] = delta_x[15] + nom_x[15];
   out_4948547112888214127[16] = delta_x[16] + nom_x[16];
   out_4948547112888214127[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1637666684293454320) {
   out_1637666684293454320[0] = -nom_x[0] + true_x[0];
   out_1637666684293454320[1] = -nom_x[1] + true_x[1];
   out_1637666684293454320[2] = -nom_x[2] + true_x[2];
   out_1637666684293454320[3] = -nom_x[3] + true_x[3];
   out_1637666684293454320[4] = -nom_x[4] + true_x[4];
   out_1637666684293454320[5] = -nom_x[5] + true_x[5];
   out_1637666684293454320[6] = -nom_x[6] + true_x[6];
   out_1637666684293454320[7] = -nom_x[7] + true_x[7];
   out_1637666684293454320[8] = -nom_x[8] + true_x[8];
   out_1637666684293454320[9] = -nom_x[9] + true_x[9];
   out_1637666684293454320[10] = -nom_x[10] + true_x[10];
   out_1637666684293454320[11] = -nom_x[11] + true_x[11];
   out_1637666684293454320[12] = -nom_x[12] + true_x[12];
   out_1637666684293454320[13] = -nom_x[13] + true_x[13];
   out_1637666684293454320[14] = -nom_x[14] + true_x[14];
   out_1637666684293454320[15] = -nom_x[15] + true_x[15];
   out_1637666684293454320[16] = -nom_x[16] + true_x[16];
   out_1637666684293454320[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2192054780204158214) {
   out_2192054780204158214[0] = 1.0;
   out_2192054780204158214[1] = 0.0;
   out_2192054780204158214[2] = 0.0;
   out_2192054780204158214[3] = 0.0;
   out_2192054780204158214[4] = 0.0;
   out_2192054780204158214[5] = 0.0;
   out_2192054780204158214[6] = 0.0;
   out_2192054780204158214[7] = 0.0;
   out_2192054780204158214[8] = 0.0;
   out_2192054780204158214[9] = 0.0;
   out_2192054780204158214[10] = 0.0;
   out_2192054780204158214[11] = 0.0;
   out_2192054780204158214[12] = 0.0;
   out_2192054780204158214[13] = 0.0;
   out_2192054780204158214[14] = 0.0;
   out_2192054780204158214[15] = 0.0;
   out_2192054780204158214[16] = 0.0;
   out_2192054780204158214[17] = 0.0;
   out_2192054780204158214[18] = 0.0;
   out_2192054780204158214[19] = 1.0;
   out_2192054780204158214[20] = 0.0;
   out_2192054780204158214[21] = 0.0;
   out_2192054780204158214[22] = 0.0;
   out_2192054780204158214[23] = 0.0;
   out_2192054780204158214[24] = 0.0;
   out_2192054780204158214[25] = 0.0;
   out_2192054780204158214[26] = 0.0;
   out_2192054780204158214[27] = 0.0;
   out_2192054780204158214[28] = 0.0;
   out_2192054780204158214[29] = 0.0;
   out_2192054780204158214[30] = 0.0;
   out_2192054780204158214[31] = 0.0;
   out_2192054780204158214[32] = 0.0;
   out_2192054780204158214[33] = 0.0;
   out_2192054780204158214[34] = 0.0;
   out_2192054780204158214[35] = 0.0;
   out_2192054780204158214[36] = 0.0;
   out_2192054780204158214[37] = 0.0;
   out_2192054780204158214[38] = 1.0;
   out_2192054780204158214[39] = 0.0;
   out_2192054780204158214[40] = 0.0;
   out_2192054780204158214[41] = 0.0;
   out_2192054780204158214[42] = 0.0;
   out_2192054780204158214[43] = 0.0;
   out_2192054780204158214[44] = 0.0;
   out_2192054780204158214[45] = 0.0;
   out_2192054780204158214[46] = 0.0;
   out_2192054780204158214[47] = 0.0;
   out_2192054780204158214[48] = 0.0;
   out_2192054780204158214[49] = 0.0;
   out_2192054780204158214[50] = 0.0;
   out_2192054780204158214[51] = 0.0;
   out_2192054780204158214[52] = 0.0;
   out_2192054780204158214[53] = 0.0;
   out_2192054780204158214[54] = 0.0;
   out_2192054780204158214[55] = 0.0;
   out_2192054780204158214[56] = 0.0;
   out_2192054780204158214[57] = 1.0;
   out_2192054780204158214[58] = 0.0;
   out_2192054780204158214[59] = 0.0;
   out_2192054780204158214[60] = 0.0;
   out_2192054780204158214[61] = 0.0;
   out_2192054780204158214[62] = 0.0;
   out_2192054780204158214[63] = 0.0;
   out_2192054780204158214[64] = 0.0;
   out_2192054780204158214[65] = 0.0;
   out_2192054780204158214[66] = 0.0;
   out_2192054780204158214[67] = 0.0;
   out_2192054780204158214[68] = 0.0;
   out_2192054780204158214[69] = 0.0;
   out_2192054780204158214[70] = 0.0;
   out_2192054780204158214[71] = 0.0;
   out_2192054780204158214[72] = 0.0;
   out_2192054780204158214[73] = 0.0;
   out_2192054780204158214[74] = 0.0;
   out_2192054780204158214[75] = 0.0;
   out_2192054780204158214[76] = 1.0;
   out_2192054780204158214[77] = 0.0;
   out_2192054780204158214[78] = 0.0;
   out_2192054780204158214[79] = 0.0;
   out_2192054780204158214[80] = 0.0;
   out_2192054780204158214[81] = 0.0;
   out_2192054780204158214[82] = 0.0;
   out_2192054780204158214[83] = 0.0;
   out_2192054780204158214[84] = 0.0;
   out_2192054780204158214[85] = 0.0;
   out_2192054780204158214[86] = 0.0;
   out_2192054780204158214[87] = 0.0;
   out_2192054780204158214[88] = 0.0;
   out_2192054780204158214[89] = 0.0;
   out_2192054780204158214[90] = 0.0;
   out_2192054780204158214[91] = 0.0;
   out_2192054780204158214[92] = 0.0;
   out_2192054780204158214[93] = 0.0;
   out_2192054780204158214[94] = 0.0;
   out_2192054780204158214[95] = 1.0;
   out_2192054780204158214[96] = 0.0;
   out_2192054780204158214[97] = 0.0;
   out_2192054780204158214[98] = 0.0;
   out_2192054780204158214[99] = 0.0;
   out_2192054780204158214[100] = 0.0;
   out_2192054780204158214[101] = 0.0;
   out_2192054780204158214[102] = 0.0;
   out_2192054780204158214[103] = 0.0;
   out_2192054780204158214[104] = 0.0;
   out_2192054780204158214[105] = 0.0;
   out_2192054780204158214[106] = 0.0;
   out_2192054780204158214[107] = 0.0;
   out_2192054780204158214[108] = 0.0;
   out_2192054780204158214[109] = 0.0;
   out_2192054780204158214[110] = 0.0;
   out_2192054780204158214[111] = 0.0;
   out_2192054780204158214[112] = 0.0;
   out_2192054780204158214[113] = 0.0;
   out_2192054780204158214[114] = 1.0;
   out_2192054780204158214[115] = 0.0;
   out_2192054780204158214[116] = 0.0;
   out_2192054780204158214[117] = 0.0;
   out_2192054780204158214[118] = 0.0;
   out_2192054780204158214[119] = 0.0;
   out_2192054780204158214[120] = 0.0;
   out_2192054780204158214[121] = 0.0;
   out_2192054780204158214[122] = 0.0;
   out_2192054780204158214[123] = 0.0;
   out_2192054780204158214[124] = 0.0;
   out_2192054780204158214[125] = 0.0;
   out_2192054780204158214[126] = 0.0;
   out_2192054780204158214[127] = 0.0;
   out_2192054780204158214[128] = 0.0;
   out_2192054780204158214[129] = 0.0;
   out_2192054780204158214[130] = 0.0;
   out_2192054780204158214[131] = 0.0;
   out_2192054780204158214[132] = 0.0;
   out_2192054780204158214[133] = 1.0;
   out_2192054780204158214[134] = 0.0;
   out_2192054780204158214[135] = 0.0;
   out_2192054780204158214[136] = 0.0;
   out_2192054780204158214[137] = 0.0;
   out_2192054780204158214[138] = 0.0;
   out_2192054780204158214[139] = 0.0;
   out_2192054780204158214[140] = 0.0;
   out_2192054780204158214[141] = 0.0;
   out_2192054780204158214[142] = 0.0;
   out_2192054780204158214[143] = 0.0;
   out_2192054780204158214[144] = 0.0;
   out_2192054780204158214[145] = 0.0;
   out_2192054780204158214[146] = 0.0;
   out_2192054780204158214[147] = 0.0;
   out_2192054780204158214[148] = 0.0;
   out_2192054780204158214[149] = 0.0;
   out_2192054780204158214[150] = 0.0;
   out_2192054780204158214[151] = 0.0;
   out_2192054780204158214[152] = 1.0;
   out_2192054780204158214[153] = 0.0;
   out_2192054780204158214[154] = 0.0;
   out_2192054780204158214[155] = 0.0;
   out_2192054780204158214[156] = 0.0;
   out_2192054780204158214[157] = 0.0;
   out_2192054780204158214[158] = 0.0;
   out_2192054780204158214[159] = 0.0;
   out_2192054780204158214[160] = 0.0;
   out_2192054780204158214[161] = 0.0;
   out_2192054780204158214[162] = 0.0;
   out_2192054780204158214[163] = 0.0;
   out_2192054780204158214[164] = 0.0;
   out_2192054780204158214[165] = 0.0;
   out_2192054780204158214[166] = 0.0;
   out_2192054780204158214[167] = 0.0;
   out_2192054780204158214[168] = 0.0;
   out_2192054780204158214[169] = 0.0;
   out_2192054780204158214[170] = 0.0;
   out_2192054780204158214[171] = 1.0;
   out_2192054780204158214[172] = 0.0;
   out_2192054780204158214[173] = 0.0;
   out_2192054780204158214[174] = 0.0;
   out_2192054780204158214[175] = 0.0;
   out_2192054780204158214[176] = 0.0;
   out_2192054780204158214[177] = 0.0;
   out_2192054780204158214[178] = 0.0;
   out_2192054780204158214[179] = 0.0;
   out_2192054780204158214[180] = 0.0;
   out_2192054780204158214[181] = 0.0;
   out_2192054780204158214[182] = 0.0;
   out_2192054780204158214[183] = 0.0;
   out_2192054780204158214[184] = 0.0;
   out_2192054780204158214[185] = 0.0;
   out_2192054780204158214[186] = 0.0;
   out_2192054780204158214[187] = 0.0;
   out_2192054780204158214[188] = 0.0;
   out_2192054780204158214[189] = 0.0;
   out_2192054780204158214[190] = 1.0;
   out_2192054780204158214[191] = 0.0;
   out_2192054780204158214[192] = 0.0;
   out_2192054780204158214[193] = 0.0;
   out_2192054780204158214[194] = 0.0;
   out_2192054780204158214[195] = 0.0;
   out_2192054780204158214[196] = 0.0;
   out_2192054780204158214[197] = 0.0;
   out_2192054780204158214[198] = 0.0;
   out_2192054780204158214[199] = 0.0;
   out_2192054780204158214[200] = 0.0;
   out_2192054780204158214[201] = 0.0;
   out_2192054780204158214[202] = 0.0;
   out_2192054780204158214[203] = 0.0;
   out_2192054780204158214[204] = 0.0;
   out_2192054780204158214[205] = 0.0;
   out_2192054780204158214[206] = 0.0;
   out_2192054780204158214[207] = 0.0;
   out_2192054780204158214[208] = 0.0;
   out_2192054780204158214[209] = 1.0;
   out_2192054780204158214[210] = 0.0;
   out_2192054780204158214[211] = 0.0;
   out_2192054780204158214[212] = 0.0;
   out_2192054780204158214[213] = 0.0;
   out_2192054780204158214[214] = 0.0;
   out_2192054780204158214[215] = 0.0;
   out_2192054780204158214[216] = 0.0;
   out_2192054780204158214[217] = 0.0;
   out_2192054780204158214[218] = 0.0;
   out_2192054780204158214[219] = 0.0;
   out_2192054780204158214[220] = 0.0;
   out_2192054780204158214[221] = 0.0;
   out_2192054780204158214[222] = 0.0;
   out_2192054780204158214[223] = 0.0;
   out_2192054780204158214[224] = 0.0;
   out_2192054780204158214[225] = 0.0;
   out_2192054780204158214[226] = 0.0;
   out_2192054780204158214[227] = 0.0;
   out_2192054780204158214[228] = 1.0;
   out_2192054780204158214[229] = 0.0;
   out_2192054780204158214[230] = 0.0;
   out_2192054780204158214[231] = 0.0;
   out_2192054780204158214[232] = 0.0;
   out_2192054780204158214[233] = 0.0;
   out_2192054780204158214[234] = 0.0;
   out_2192054780204158214[235] = 0.0;
   out_2192054780204158214[236] = 0.0;
   out_2192054780204158214[237] = 0.0;
   out_2192054780204158214[238] = 0.0;
   out_2192054780204158214[239] = 0.0;
   out_2192054780204158214[240] = 0.0;
   out_2192054780204158214[241] = 0.0;
   out_2192054780204158214[242] = 0.0;
   out_2192054780204158214[243] = 0.0;
   out_2192054780204158214[244] = 0.0;
   out_2192054780204158214[245] = 0.0;
   out_2192054780204158214[246] = 0.0;
   out_2192054780204158214[247] = 1.0;
   out_2192054780204158214[248] = 0.0;
   out_2192054780204158214[249] = 0.0;
   out_2192054780204158214[250] = 0.0;
   out_2192054780204158214[251] = 0.0;
   out_2192054780204158214[252] = 0.0;
   out_2192054780204158214[253] = 0.0;
   out_2192054780204158214[254] = 0.0;
   out_2192054780204158214[255] = 0.0;
   out_2192054780204158214[256] = 0.0;
   out_2192054780204158214[257] = 0.0;
   out_2192054780204158214[258] = 0.0;
   out_2192054780204158214[259] = 0.0;
   out_2192054780204158214[260] = 0.0;
   out_2192054780204158214[261] = 0.0;
   out_2192054780204158214[262] = 0.0;
   out_2192054780204158214[263] = 0.0;
   out_2192054780204158214[264] = 0.0;
   out_2192054780204158214[265] = 0.0;
   out_2192054780204158214[266] = 1.0;
   out_2192054780204158214[267] = 0.0;
   out_2192054780204158214[268] = 0.0;
   out_2192054780204158214[269] = 0.0;
   out_2192054780204158214[270] = 0.0;
   out_2192054780204158214[271] = 0.0;
   out_2192054780204158214[272] = 0.0;
   out_2192054780204158214[273] = 0.0;
   out_2192054780204158214[274] = 0.0;
   out_2192054780204158214[275] = 0.0;
   out_2192054780204158214[276] = 0.0;
   out_2192054780204158214[277] = 0.0;
   out_2192054780204158214[278] = 0.0;
   out_2192054780204158214[279] = 0.0;
   out_2192054780204158214[280] = 0.0;
   out_2192054780204158214[281] = 0.0;
   out_2192054780204158214[282] = 0.0;
   out_2192054780204158214[283] = 0.0;
   out_2192054780204158214[284] = 0.0;
   out_2192054780204158214[285] = 1.0;
   out_2192054780204158214[286] = 0.0;
   out_2192054780204158214[287] = 0.0;
   out_2192054780204158214[288] = 0.0;
   out_2192054780204158214[289] = 0.0;
   out_2192054780204158214[290] = 0.0;
   out_2192054780204158214[291] = 0.0;
   out_2192054780204158214[292] = 0.0;
   out_2192054780204158214[293] = 0.0;
   out_2192054780204158214[294] = 0.0;
   out_2192054780204158214[295] = 0.0;
   out_2192054780204158214[296] = 0.0;
   out_2192054780204158214[297] = 0.0;
   out_2192054780204158214[298] = 0.0;
   out_2192054780204158214[299] = 0.0;
   out_2192054780204158214[300] = 0.0;
   out_2192054780204158214[301] = 0.0;
   out_2192054780204158214[302] = 0.0;
   out_2192054780204158214[303] = 0.0;
   out_2192054780204158214[304] = 1.0;
   out_2192054780204158214[305] = 0.0;
   out_2192054780204158214[306] = 0.0;
   out_2192054780204158214[307] = 0.0;
   out_2192054780204158214[308] = 0.0;
   out_2192054780204158214[309] = 0.0;
   out_2192054780204158214[310] = 0.0;
   out_2192054780204158214[311] = 0.0;
   out_2192054780204158214[312] = 0.0;
   out_2192054780204158214[313] = 0.0;
   out_2192054780204158214[314] = 0.0;
   out_2192054780204158214[315] = 0.0;
   out_2192054780204158214[316] = 0.0;
   out_2192054780204158214[317] = 0.0;
   out_2192054780204158214[318] = 0.0;
   out_2192054780204158214[319] = 0.0;
   out_2192054780204158214[320] = 0.0;
   out_2192054780204158214[321] = 0.0;
   out_2192054780204158214[322] = 0.0;
   out_2192054780204158214[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8699512147542263638) {
   out_8699512147542263638[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8699512147542263638[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8699512147542263638[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8699512147542263638[3] = dt*state[12] + state[3];
   out_8699512147542263638[4] = dt*state[13] + state[4];
   out_8699512147542263638[5] = dt*state[14] + state[5];
   out_8699512147542263638[6] = state[6];
   out_8699512147542263638[7] = state[7];
   out_8699512147542263638[8] = state[8];
   out_8699512147542263638[9] = state[9];
   out_8699512147542263638[10] = state[10];
   out_8699512147542263638[11] = state[11];
   out_8699512147542263638[12] = state[12];
   out_8699512147542263638[13] = state[13];
   out_8699512147542263638[14] = state[14];
   out_8699512147542263638[15] = state[15];
   out_8699512147542263638[16] = state[16];
   out_8699512147542263638[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5585604130229028810) {
   out_5585604130229028810[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5585604130229028810[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5585604130229028810[2] = 0;
   out_5585604130229028810[3] = 0;
   out_5585604130229028810[4] = 0;
   out_5585604130229028810[5] = 0;
   out_5585604130229028810[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5585604130229028810[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5585604130229028810[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5585604130229028810[9] = 0;
   out_5585604130229028810[10] = 0;
   out_5585604130229028810[11] = 0;
   out_5585604130229028810[12] = 0;
   out_5585604130229028810[13] = 0;
   out_5585604130229028810[14] = 0;
   out_5585604130229028810[15] = 0;
   out_5585604130229028810[16] = 0;
   out_5585604130229028810[17] = 0;
   out_5585604130229028810[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5585604130229028810[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5585604130229028810[20] = 0;
   out_5585604130229028810[21] = 0;
   out_5585604130229028810[22] = 0;
   out_5585604130229028810[23] = 0;
   out_5585604130229028810[24] = 0;
   out_5585604130229028810[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5585604130229028810[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5585604130229028810[27] = 0;
   out_5585604130229028810[28] = 0;
   out_5585604130229028810[29] = 0;
   out_5585604130229028810[30] = 0;
   out_5585604130229028810[31] = 0;
   out_5585604130229028810[32] = 0;
   out_5585604130229028810[33] = 0;
   out_5585604130229028810[34] = 0;
   out_5585604130229028810[35] = 0;
   out_5585604130229028810[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5585604130229028810[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5585604130229028810[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5585604130229028810[39] = 0;
   out_5585604130229028810[40] = 0;
   out_5585604130229028810[41] = 0;
   out_5585604130229028810[42] = 0;
   out_5585604130229028810[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5585604130229028810[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5585604130229028810[45] = 0;
   out_5585604130229028810[46] = 0;
   out_5585604130229028810[47] = 0;
   out_5585604130229028810[48] = 0;
   out_5585604130229028810[49] = 0;
   out_5585604130229028810[50] = 0;
   out_5585604130229028810[51] = 0;
   out_5585604130229028810[52] = 0;
   out_5585604130229028810[53] = 0;
   out_5585604130229028810[54] = 0;
   out_5585604130229028810[55] = 0;
   out_5585604130229028810[56] = 0;
   out_5585604130229028810[57] = 1;
   out_5585604130229028810[58] = 0;
   out_5585604130229028810[59] = 0;
   out_5585604130229028810[60] = 0;
   out_5585604130229028810[61] = 0;
   out_5585604130229028810[62] = 0;
   out_5585604130229028810[63] = 0;
   out_5585604130229028810[64] = 0;
   out_5585604130229028810[65] = 0;
   out_5585604130229028810[66] = dt;
   out_5585604130229028810[67] = 0;
   out_5585604130229028810[68] = 0;
   out_5585604130229028810[69] = 0;
   out_5585604130229028810[70] = 0;
   out_5585604130229028810[71] = 0;
   out_5585604130229028810[72] = 0;
   out_5585604130229028810[73] = 0;
   out_5585604130229028810[74] = 0;
   out_5585604130229028810[75] = 0;
   out_5585604130229028810[76] = 1;
   out_5585604130229028810[77] = 0;
   out_5585604130229028810[78] = 0;
   out_5585604130229028810[79] = 0;
   out_5585604130229028810[80] = 0;
   out_5585604130229028810[81] = 0;
   out_5585604130229028810[82] = 0;
   out_5585604130229028810[83] = 0;
   out_5585604130229028810[84] = 0;
   out_5585604130229028810[85] = dt;
   out_5585604130229028810[86] = 0;
   out_5585604130229028810[87] = 0;
   out_5585604130229028810[88] = 0;
   out_5585604130229028810[89] = 0;
   out_5585604130229028810[90] = 0;
   out_5585604130229028810[91] = 0;
   out_5585604130229028810[92] = 0;
   out_5585604130229028810[93] = 0;
   out_5585604130229028810[94] = 0;
   out_5585604130229028810[95] = 1;
   out_5585604130229028810[96] = 0;
   out_5585604130229028810[97] = 0;
   out_5585604130229028810[98] = 0;
   out_5585604130229028810[99] = 0;
   out_5585604130229028810[100] = 0;
   out_5585604130229028810[101] = 0;
   out_5585604130229028810[102] = 0;
   out_5585604130229028810[103] = 0;
   out_5585604130229028810[104] = dt;
   out_5585604130229028810[105] = 0;
   out_5585604130229028810[106] = 0;
   out_5585604130229028810[107] = 0;
   out_5585604130229028810[108] = 0;
   out_5585604130229028810[109] = 0;
   out_5585604130229028810[110] = 0;
   out_5585604130229028810[111] = 0;
   out_5585604130229028810[112] = 0;
   out_5585604130229028810[113] = 0;
   out_5585604130229028810[114] = 1;
   out_5585604130229028810[115] = 0;
   out_5585604130229028810[116] = 0;
   out_5585604130229028810[117] = 0;
   out_5585604130229028810[118] = 0;
   out_5585604130229028810[119] = 0;
   out_5585604130229028810[120] = 0;
   out_5585604130229028810[121] = 0;
   out_5585604130229028810[122] = 0;
   out_5585604130229028810[123] = 0;
   out_5585604130229028810[124] = 0;
   out_5585604130229028810[125] = 0;
   out_5585604130229028810[126] = 0;
   out_5585604130229028810[127] = 0;
   out_5585604130229028810[128] = 0;
   out_5585604130229028810[129] = 0;
   out_5585604130229028810[130] = 0;
   out_5585604130229028810[131] = 0;
   out_5585604130229028810[132] = 0;
   out_5585604130229028810[133] = 1;
   out_5585604130229028810[134] = 0;
   out_5585604130229028810[135] = 0;
   out_5585604130229028810[136] = 0;
   out_5585604130229028810[137] = 0;
   out_5585604130229028810[138] = 0;
   out_5585604130229028810[139] = 0;
   out_5585604130229028810[140] = 0;
   out_5585604130229028810[141] = 0;
   out_5585604130229028810[142] = 0;
   out_5585604130229028810[143] = 0;
   out_5585604130229028810[144] = 0;
   out_5585604130229028810[145] = 0;
   out_5585604130229028810[146] = 0;
   out_5585604130229028810[147] = 0;
   out_5585604130229028810[148] = 0;
   out_5585604130229028810[149] = 0;
   out_5585604130229028810[150] = 0;
   out_5585604130229028810[151] = 0;
   out_5585604130229028810[152] = 1;
   out_5585604130229028810[153] = 0;
   out_5585604130229028810[154] = 0;
   out_5585604130229028810[155] = 0;
   out_5585604130229028810[156] = 0;
   out_5585604130229028810[157] = 0;
   out_5585604130229028810[158] = 0;
   out_5585604130229028810[159] = 0;
   out_5585604130229028810[160] = 0;
   out_5585604130229028810[161] = 0;
   out_5585604130229028810[162] = 0;
   out_5585604130229028810[163] = 0;
   out_5585604130229028810[164] = 0;
   out_5585604130229028810[165] = 0;
   out_5585604130229028810[166] = 0;
   out_5585604130229028810[167] = 0;
   out_5585604130229028810[168] = 0;
   out_5585604130229028810[169] = 0;
   out_5585604130229028810[170] = 0;
   out_5585604130229028810[171] = 1;
   out_5585604130229028810[172] = 0;
   out_5585604130229028810[173] = 0;
   out_5585604130229028810[174] = 0;
   out_5585604130229028810[175] = 0;
   out_5585604130229028810[176] = 0;
   out_5585604130229028810[177] = 0;
   out_5585604130229028810[178] = 0;
   out_5585604130229028810[179] = 0;
   out_5585604130229028810[180] = 0;
   out_5585604130229028810[181] = 0;
   out_5585604130229028810[182] = 0;
   out_5585604130229028810[183] = 0;
   out_5585604130229028810[184] = 0;
   out_5585604130229028810[185] = 0;
   out_5585604130229028810[186] = 0;
   out_5585604130229028810[187] = 0;
   out_5585604130229028810[188] = 0;
   out_5585604130229028810[189] = 0;
   out_5585604130229028810[190] = 1;
   out_5585604130229028810[191] = 0;
   out_5585604130229028810[192] = 0;
   out_5585604130229028810[193] = 0;
   out_5585604130229028810[194] = 0;
   out_5585604130229028810[195] = 0;
   out_5585604130229028810[196] = 0;
   out_5585604130229028810[197] = 0;
   out_5585604130229028810[198] = 0;
   out_5585604130229028810[199] = 0;
   out_5585604130229028810[200] = 0;
   out_5585604130229028810[201] = 0;
   out_5585604130229028810[202] = 0;
   out_5585604130229028810[203] = 0;
   out_5585604130229028810[204] = 0;
   out_5585604130229028810[205] = 0;
   out_5585604130229028810[206] = 0;
   out_5585604130229028810[207] = 0;
   out_5585604130229028810[208] = 0;
   out_5585604130229028810[209] = 1;
   out_5585604130229028810[210] = 0;
   out_5585604130229028810[211] = 0;
   out_5585604130229028810[212] = 0;
   out_5585604130229028810[213] = 0;
   out_5585604130229028810[214] = 0;
   out_5585604130229028810[215] = 0;
   out_5585604130229028810[216] = 0;
   out_5585604130229028810[217] = 0;
   out_5585604130229028810[218] = 0;
   out_5585604130229028810[219] = 0;
   out_5585604130229028810[220] = 0;
   out_5585604130229028810[221] = 0;
   out_5585604130229028810[222] = 0;
   out_5585604130229028810[223] = 0;
   out_5585604130229028810[224] = 0;
   out_5585604130229028810[225] = 0;
   out_5585604130229028810[226] = 0;
   out_5585604130229028810[227] = 0;
   out_5585604130229028810[228] = 1;
   out_5585604130229028810[229] = 0;
   out_5585604130229028810[230] = 0;
   out_5585604130229028810[231] = 0;
   out_5585604130229028810[232] = 0;
   out_5585604130229028810[233] = 0;
   out_5585604130229028810[234] = 0;
   out_5585604130229028810[235] = 0;
   out_5585604130229028810[236] = 0;
   out_5585604130229028810[237] = 0;
   out_5585604130229028810[238] = 0;
   out_5585604130229028810[239] = 0;
   out_5585604130229028810[240] = 0;
   out_5585604130229028810[241] = 0;
   out_5585604130229028810[242] = 0;
   out_5585604130229028810[243] = 0;
   out_5585604130229028810[244] = 0;
   out_5585604130229028810[245] = 0;
   out_5585604130229028810[246] = 0;
   out_5585604130229028810[247] = 1;
   out_5585604130229028810[248] = 0;
   out_5585604130229028810[249] = 0;
   out_5585604130229028810[250] = 0;
   out_5585604130229028810[251] = 0;
   out_5585604130229028810[252] = 0;
   out_5585604130229028810[253] = 0;
   out_5585604130229028810[254] = 0;
   out_5585604130229028810[255] = 0;
   out_5585604130229028810[256] = 0;
   out_5585604130229028810[257] = 0;
   out_5585604130229028810[258] = 0;
   out_5585604130229028810[259] = 0;
   out_5585604130229028810[260] = 0;
   out_5585604130229028810[261] = 0;
   out_5585604130229028810[262] = 0;
   out_5585604130229028810[263] = 0;
   out_5585604130229028810[264] = 0;
   out_5585604130229028810[265] = 0;
   out_5585604130229028810[266] = 1;
   out_5585604130229028810[267] = 0;
   out_5585604130229028810[268] = 0;
   out_5585604130229028810[269] = 0;
   out_5585604130229028810[270] = 0;
   out_5585604130229028810[271] = 0;
   out_5585604130229028810[272] = 0;
   out_5585604130229028810[273] = 0;
   out_5585604130229028810[274] = 0;
   out_5585604130229028810[275] = 0;
   out_5585604130229028810[276] = 0;
   out_5585604130229028810[277] = 0;
   out_5585604130229028810[278] = 0;
   out_5585604130229028810[279] = 0;
   out_5585604130229028810[280] = 0;
   out_5585604130229028810[281] = 0;
   out_5585604130229028810[282] = 0;
   out_5585604130229028810[283] = 0;
   out_5585604130229028810[284] = 0;
   out_5585604130229028810[285] = 1;
   out_5585604130229028810[286] = 0;
   out_5585604130229028810[287] = 0;
   out_5585604130229028810[288] = 0;
   out_5585604130229028810[289] = 0;
   out_5585604130229028810[290] = 0;
   out_5585604130229028810[291] = 0;
   out_5585604130229028810[292] = 0;
   out_5585604130229028810[293] = 0;
   out_5585604130229028810[294] = 0;
   out_5585604130229028810[295] = 0;
   out_5585604130229028810[296] = 0;
   out_5585604130229028810[297] = 0;
   out_5585604130229028810[298] = 0;
   out_5585604130229028810[299] = 0;
   out_5585604130229028810[300] = 0;
   out_5585604130229028810[301] = 0;
   out_5585604130229028810[302] = 0;
   out_5585604130229028810[303] = 0;
   out_5585604130229028810[304] = 1;
   out_5585604130229028810[305] = 0;
   out_5585604130229028810[306] = 0;
   out_5585604130229028810[307] = 0;
   out_5585604130229028810[308] = 0;
   out_5585604130229028810[309] = 0;
   out_5585604130229028810[310] = 0;
   out_5585604130229028810[311] = 0;
   out_5585604130229028810[312] = 0;
   out_5585604130229028810[313] = 0;
   out_5585604130229028810[314] = 0;
   out_5585604130229028810[315] = 0;
   out_5585604130229028810[316] = 0;
   out_5585604130229028810[317] = 0;
   out_5585604130229028810[318] = 0;
   out_5585604130229028810[319] = 0;
   out_5585604130229028810[320] = 0;
   out_5585604130229028810[321] = 0;
   out_5585604130229028810[322] = 0;
   out_5585604130229028810[323] = 1;
}
void h_4(double *state, double *unused, double *out_7040990451462861704) {
   out_7040990451462861704[0] = state[6] + state[9];
   out_7040990451462861704[1] = state[7] + state[10];
   out_7040990451462861704[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8084524700677117702) {
   out_8084524700677117702[0] = 0;
   out_8084524700677117702[1] = 0;
   out_8084524700677117702[2] = 0;
   out_8084524700677117702[3] = 0;
   out_8084524700677117702[4] = 0;
   out_8084524700677117702[5] = 0;
   out_8084524700677117702[6] = 1;
   out_8084524700677117702[7] = 0;
   out_8084524700677117702[8] = 0;
   out_8084524700677117702[9] = 1;
   out_8084524700677117702[10] = 0;
   out_8084524700677117702[11] = 0;
   out_8084524700677117702[12] = 0;
   out_8084524700677117702[13] = 0;
   out_8084524700677117702[14] = 0;
   out_8084524700677117702[15] = 0;
   out_8084524700677117702[16] = 0;
   out_8084524700677117702[17] = 0;
   out_8084524700677117702[18] = 0;
   out_8084524700677117702[19] = 0;
   out_8084524700677117702[20] = 0;
   out_8084524700677117702[21] = 0;
   out_8084524700677117702[22] = 0;
   out_8084524700677117702[23] = 0;
   out_8084524700677117702[24] = 0;
   out_8084524700677117702[25] = 1;
   out_8084524700677117702[26] = 0;
   out_8084524700677117702[27] = 0;
   out_8084524700677117702[28] = 1;
   out_8084524700677117702[29] = 0;
   out_8084524700677117702[30] = 0;
   out_8084524700677117702[31] = 0;
   out_8084524700677117702[32] = 0;
   out_8084524700677117702[33] = 0;
   out_8084524700677117702[34] = 0;
   out_8084524700677117702[35] = 0;
   out_8084524700677117702[36] = 0;
   out_8084524700677117702[37] = 0;
   out_8084524700677117702[38] = 0;
   out_8084524700677117702[39] = 0;
   out_8084524700677117702[40] = 0;
   out_8084524700677117702[41] = 0;
   out_8084524700677117702[42] = 0;
   out_8084524700677117702[43] = 0;
   out_8084524700677117702[44] = 1;
   out_8084524700677117702[45] = 0;
   out_8084524700677117702[46] = 0;
   out_8084524700677117702[47] = 1;
   out_8084524700677117702[48] = 0;
   out_8084524700677117702[49] = 0;
   out_8084524700677117702[50] = 0;
   out_8084524700677117702[51] = 0;
   out_8084524700677117702[52] = 0;
   out_8084524700677117702[53] = 0;
}
void h_10(double *state, double *unused, double *out_5385759793768973690) {
   out_5385759793768973690[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5385759793768973690[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5385759793768973690[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_522586112484741399) {
   out_522586112484741399[0] = 0;
   out_522586112484741399[1] = 9.8100000000000005*cos(state[1]);
   out_522586112484741399[2] = 0;
   out_522586112484741399[3] = 0;
   out_522586112484741399[4] = -state[8];
   out_522586112484741399[5] = state[7];
   out_522586112484741399[6] = 0;
   out_522586112484741399[7] = state[5];
   out_522586112484741399[8] = -state[4];
   out_522586112484741399[9] = 0;
   out_522586112484741399[10] = 0;
   out_522586112484741399[11] = 0;
   out_522586112484741399[12] = 1;
   out_522586112484741399[13] = 0;
   out_522586112484741399[14] = 0;
   out_522586112484741399[15] = 1;
   out_522586112484741399[16] = 0;
   out_522586112484741399[17] = 0;
   out_522586112484741399[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_522586112484741399[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_522586112484741399[20] = 0;
   out_522586112484741399[21] = state[8];
   out_522586112484741399[22] = 0;
   out_522586112484741399[23] = -state[6];
   out_522586112484741399[24] = -state[5];
   out_522586112484741399[25] = 0;
   out_522586112484741399[26] = state[3];
   out_522586112484741399[27] = 0;
   out_522586112484741399[28] = 0;
   out_522586112484741399[29] = 0;
   out_522586112484741399[30] = 0;
   out_522586112484741399[31] = 1;
   out_522586112484741399[32] = 0;
   out_522586112484741399[33] = 0;
   out_522586112484741399[34] = 1;
   out_522586112484741399[35] = 0;
   out_522586112484741399[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_522586112484741399[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_522586112484741399[38] = 0;
   out_522586112484741399[39] = -state[7];
   out_522586112484741399[40] = state[6];
   out_522586112484741399[41] = 0;
   out_522586112484741399[42] = state[4];
   out_522586112484741399[43] = -state[3];
   out_522586112484741399[44] = 0;
   out_522586112484741399[45] = 0;
   out_522586112484741399[46] = 0;
   out_522586112484741399[47] = 0;
   out_522586112484741399[48] = 0;
   out_522586112484741399[49] = 0;
   out_522586112484741399[50] = 1;
   out_522586112484741399[51] = 0;
   out_522586112484741399[52] = 0;
   out_522586112484741399[53] = 1;
}
void h_13(double *state, double *unused, double *out_1659773189667427592) {
   out_1659773189667427592[0] = state[3];
   out_1659773189667427592[1] = state[4];
   out_1659773189667427592[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4872250875344784901) {
   out_4872250875344784901[0] = 0;
   out_4872250875344784901[1] = 0;
   out_4872250875344784901[2] = 0;
   out_4872250875344784901[3] = 1;
   out_4872250875344784901[4] = 0;
   out_4872250875344784901[5] = 0;
   out_4872250875344784901[6] = 0;
   out_4872250875344784901[7] = 0;
   out_4872250875344784901[8] = 0;
   out_4872250875344784901[9] = 0;
   out_4872250875344784901[10] = 0;
   out_4872250875344784901[11] = 0;
   out_4872250875344784901[12] = 0;
   out_4872250875344784901[13] = 0;
   out_4872250875344784901[14] = 0;
   out_4872250875344784901[15] = 0;
   out_4872250875344784901[16] = 0;
   out_4872250875344784901[17] = 0;
   out_4872250875344784901[18] = 0;
   out_4872250875344784901[19] = 0;
   out_4872250875344784901[20] = 0;
   out_4872250875344784901[21] = 0;
   out_4872250875344784901[22] = 1;
   out_4872250875344784901[23] = 0;
   out_4872250875344784901[24] = 0;
   out_4872250875344784901[25] = 0;
   out_4872250875344784901[26] = 0;
   out_4872250875344784901[27] = 0;
   out_4872250875344784901[28] = 0;
   out_4872250875344784901[29] = 0;
   out_4872250875344784901[30] = 0;
   out_4872250875344784901[31] = 0;
   out_4872250875344784901[32] = 0;
   out_4872250875344784901[33] = 0;
   out_4872250875344784901[34] = 0;
   out_4872250875344784901[35] = 0;
   out_4872250875344784901[36] = 0;
   out_4872250875344784901[37] = 0;
   out_4872250875344784901[38] = 0;
   out_4872250875344784901[39] = 0;
   out_4872250875344784901[40] = 0;
   out_4872250875344784901[41] = 1;
   out_4872250875344784901[42] = 0;
   out_4872250875344784901[43] = 0;
   out_4872250875344784901[44] = 0;
   out_4872250875344784901[45] = 0;
   out_4872250875344784901[46] = 0;
   out_4872250875344784901[47] = 0;
   out_4872250875344784901[48] = 0;
   out_4872250875344784901[49] = 0;
   out_4872250875344784901[50] = 0;
   out_4872250875344784901[51] = 0;
   out_4872250875344784901[52] = 0;
   out_4872250875344784901[53] = 0;
}
void h_14(double *state, double *unused, double *out_6941415956428537191) {
   out_6941415956428537191[0] = state[6];
   out_6941415956428537191[1] = state[7];
   out_6941415956428537191[2] = state[8];
}
void H_14(double *state, double *unused, double *out_8519641227322001301) {
   out_8519641227322001301[0] = 0;
   out_8519641227322001301[1] = 0;
   out_8519641227322001301[2] = 0;
   out_8519641227322001301[3] = 0;
   out_8519641227322001301[4] = 0;
   out_8519641227322001301[5] = 0;
   out_8519641227322001301[6] = 1;
   out_8519641227322001301[7] = 0;
   out_8519641227322001301[8] = 0;
   out_8519641227322001301[9] = 0;
   out_8519641227322001301[10] = 0;
   out_8519641227322001301[11] = 0;
   out_8519641227322001301[12] = 0;
   out_8519641227322001301[13] = 0;
   out_8519641227322001301[14] = 0;
   out_8519641227322001301[15] = 0;
   out_8519641227322001301[16] = 0;
   out_8519641227322001301[17] = 0;
   out_8519641227322001301[18] = 0;
   out_8519641227322001301[19] = 0;
   out_8519641227322001301[20] = 0;
   out_8519641227322001301[21] = 0;
   out_8519641227322001301[22] = 0;
   out_8519641227322001301[23] = 0;
   out_8519641227322001301[24] = 0;
   out_8519641227322001301[25] = 1;
   out_8519641227322001301[26] = 0;
   out_8519641227322001301[27] = 0;
   out_8519641227322001301[28] = 0;
   out_8519641227322001301[29] = 0;
   out_8519641227322001301[30] = 0;
   out_8519641227322001301[31] = 0;
   out_8519641227322001301[32] = 0;
   out_8519641227322001301[33] = 0;
   out_8519641227322001301[34] = 0;
   out_8519641227322001301[35] = 0;
   out_8519641227322001301[36] = 0;
   out_8519641227322001301[37] = 0;
   out_8519641227322001301[38] = 0;
   out_8519641227322001301[39] = 0;
   out_8519641227322001301[40] = 0;
   out_8519641227322001301[41] = 0;
   out_8519641227322001301[42] = 0;
   out_8519641227322001301[43] = 0;
   out_8519641227322001301[44] = 1;
   out_8519641227322001301[45] = 0;
   out_8519641227322001301[46] = 0;
   out_8519641227322001301[47] = 0;
   out_8519641227322001301[48] = 0;
   out_8519641227322001301[49] = 0;
   out_8519641227322001301[50] = 0;
   out_8519641227322001301[51] = 0;
   out_8519641227322001301[52] = 0;
   out_8519641227322001301[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4948547112888214127) {
  err_fun(nom_x, delta_x, out_4948547112888214127);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1637666684293454320) {
  inv_err_fun(nom_x, true_x, out_1637666684293454320);
}
void pose_H_mod_fun(double *state, double *out_2192054780204158214) {
  H_mod_fun(state, out_2192054780204158214);
}
void pose_f_fun(double *state, double dt, double *out_8699512147542263638) {
  f_fun(state,  dt, out_8699512147542263638);
}
void pose_F_fun(double *state, double dt, double *out_5585604130229028810) {
  F_fun(state,  dt, out_5585604130229028810);
}
void pose_h_4(double *state, double *unused, double *out_7040990451462861704) {
  h_4(state, unused, out_7040990451462861704);
}
void pose_H_4(double *state, double *unused, double *out_8084524700677117702) {
  H_4(state, unused, out_8084524700677117702);
}
void pose_h_10(double *state, double *unused, double *out_5385759793768973690) {
  h_10(state, unused, out_5385759793768973690);
}
void pose_H_10(double *state, double *unused, double *out_522586112484741399) {
  H_10(state, unused, out_522586112484741399);
}
void pose_h_13(double *state, double *unused, double *out_1659773189667427592) {
  h_13(state, unused, out_1659773189667427592);
}
void pose_H_13(double *state, double *unused, double *out_4872250875344784901) {
  H_13(state, unused, out_4872250875344784901);
}
void pose_h_14(double *state, double *unused, double *out_6941415956428537191) {
  h_14(state, unused, out_6941415956428537191);
}
void pose_H_14(double *state, double *unused, double *out_8519641227322001301) {
  H_14(state, unused, out_8519641227322001301);
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
