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
void err_fun(double *nom_x, double *delta_x, double *out_4597586283991589707) {
   out_4597586283991589707[0] = delta_x[0] + nom_x[0];
   out_4597586283991589707[1] = delta_x[1] + nom_x[1];
   out_4597586283991589707[2] = delta_x[2] + nom_x[2];
   out_4597586283991589707[3] = delta_x[3] + nom_x[3];
   out_4597586283991589707[4] = delta_x[4] + nom_x[4];
   out_4597586283991589707[5] = delta_x[5] + nom_x[5];
   out_4597586283991589707[6] = delta_x[6] + nom_x[6];
   out_4597586283991589707[7] = delta_x[7] + nom_x[7];
   out_4597586283991589707[8] = delta_x[8] + nom_x[8];
   out_4597586283991589707[9] = delta_x[9] + nom_x[9];
   out_4597586283991589707[10] = delta_x[10] + nom_x[10];
   out_4597586283991589707[11] = delta_x[11] + nom_x[11];
   out_4597586283991589707[12] = delta_x[12] + nom_x[12];
   out_4597586283991589707[13] = delta_x[13] + nom_x[13];
   out_4597586283991589707[14] = delta_x[14] + nom_x[14];
   out_4597586283991589707[15] = delta_x[15] + nom_x[15];
   out_4597586283991589707[16] = delta_x[16] + nom_x[16];
   out_4597586283991589707[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2969881635711261724) {
   out_2969881635711261724[0] = -nom_x[0] + true_x[0];
   out_2969881635711261724[1] = -nom_x[1] + true_x[1];
   out_2969881635711261724[2] = -nom_x[2] + true_x[2];
   out_2969881635711261724[3] = -nom_x[3] + true_x[3];
   out_2969881635711261724[4] = -nom_x[4] + true_x[4];
   out_2969881635711261724[5] = -nom_x[5] + true_x[5];
   out_2969881635711261724[6] = -nom_x[6] + true_x[6];
   out_2969881635711261724[7] = -nom_x[7] + true_x[7];
   out_2969881635711261724[8] = -nom_x[8] + true_x[8];
   out_2969881635711261724[9] = -nom_x[9] + true_x[9];
   out_2969881635711261724[10] = -nom_x[10] + true_x[10];
   out_2969881635711261724[11] = -nom_x[11] + true_x[11];
   out_2969881635711261724[12] = -nom_x[12] + true_x[12];
   out_2969881635711261724[13] = -nom_x[13] + true_x[13];
   out_2969881635711261724[14] = -nom_x[14] + true_x[14];
   out_2969881635711261724[15] = -nom_x[15] + true_x[15];
   out_2969881635711261724[16] = -nom_x[16] + true_x[16];
   out_2969881635711261724[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7794323724515120914) {
   out_7794323724515120914[0] = 1.0;
   out_7794323724515120914[1] = 0.0;
   out_7794323724515120914[2] = 0.0;
   out_7794323724515120914[3] = 0.0;
   out_7794323724515120914[4] = 0.0;
   out_7794323724515120914[5] = 0.0;
   out_7794323724515120914[6] = 0.0;
   out_7794323724515120914[7] = 0.0;
   out_7794323724515120914[8] = 0.0;
   out_7794323724515120914[9] = 0.0;
   out_7794323724515120914[10] = 0.0;
   out_7794323724515120914[11] = 0.0;
   out_7794323724515120914[12] = 0.0;
   out_7794323724515120914[13] = 0.0;
   out_7794323724515120914[14] = 0.0;
   out_7794323724515120914[15] = 0.0;
   out_7794323724515120914[16] = 0.0;
   out_7794323724515120914[17] = 0.0;
   out_7794323724515120914[18] = 0.0;
   out_7794323724515120914[19] = 1.0;
   out_7794323724515120914[20] = 0.0;
   out_7794323724515120914[21] = 0.0;
   out_7794323724515120914[22] = 0.0;
   out_7794323724515120914[23] = 0.0;
   out_7794323724515120914[24] = 0.0;
   out_7794323724515120914[25] = 0.0;
   out_7794323724515120914[26] = 0.0;
   out_7794323724515120914[27] = 0.0;
   out_7794323724515120914[28] = 0.0;
   out_7794323724515120914[29] = 0.0;
   out_7794323724515120914[30] = 0.0;
   out_7794323724515120914[31] = 0.0;
   out_7794323724515120914[32] = 0.0;
   out_7794323724515120914[33] = 0.0;
   out_7794323724515120914[34] = 0.0;
   out_7794323724515120914[35] = 0.0;
   out_7794323724515120914[36] = 0.0;
   out_7794323724515120914[37] = 0.0;
   out_7794323724515120914[38] = 1.0;
   out_7794323724515120914[39] = 0.0;
   out_7794323724515120914[40] = 0.0;
   out_7794323724515120914[41] = 0.0;
   out_7794323724515120914[42] = 0.0;
   out_7794323724515120914[43] = 0.0;
   out_7794323724515120914[44] = 0.0;
   out_7794323724515120914[45] = 0.0;
   out_7794323724515120914[46] = 0.0;
   out_7794323724515120914[47] = 0.0;
   out_7794323724515120914[48] = 0.0;
   out_7794323724515120914[49] = 0.0;
   out_7794323724515120914[50] = 0.0;
   out_7794323724515120914[51] = 0.0;
   out_7794323724515120914[52] = 0.0;
   out_7794323724515120914[53] = 0.0;
   out_7794323724515120914[54] = 0.0;
   out_7794323724515120914[55] = 0.0;
   out_7794323724515120914[56] = 0.0;
   out_7794323724515120914[57] = 1.0;
   out_7794323724515120914[58] = 0.0;
   out_7794323724515120914[59] = 0.0;
   out_7794323724515120914[60] = 0.0;
   out_7794323724515120914[61] = 0.0;
   out_7794323724515120914[62] = 0.0;
   out_7794323724515120914[63] = 0.0;
   out_7794323724515120914[64] = 0.0;
   out_7794323724515120914[65] = 0.0;
   out_7794323724515120914[66] = 0.0;
   out_7794323724515120914[67] = 0.0;
   out_7794323724515120914[68] = 0.0;
   out_7794323724515120914[69] = 0.0;
   out_7794323724515120914[70] = 0.0;
   out_7794323724515120914[71] = 0.0;
   out_7794323724515120914[72] = 0.0;
   out_7794323724515120914[73] = 0.0;
   out_7794323724515120914[74] = 0.0;
   out_7794323724515120914[75] = 0.0;
   out_7794323724515120914[76] = 1.0;
   out_7794323724515120914[77] = 0.0;
   out_7794323724515120914[78] = 0.0;
   out_7794323724515120914[79] = 0.0;
   out_7794323724515120914[80] = 0.0;
   out_7794323724515120914[81] = 0.0;
   out_7794323724515120914[82] = 0.0;
   out_7794323724515120914[83] = 0.0;
   out_7794323724515120914[84] = 0.0;
   out_7794323724515120914[85] = 0.0;
   out_7794323724515120914[86] = 0.0;
   out_7794323724515120914[87] = 0.0;
   out_7794323724515120914[88] = 0.0;
   out_7794323724515120914[89] = 0.0;
   out_7794323724515120914[90] = 0.0;
   out_7794323724515120914[91] = 0.0;
   out_7794323724515120914[92] = 0.0;
   out_7794323724515120914[93] = 0.0;
   out_7794323724515120914[94] = 0.0;
   out_7794323724515120914[95] = 1.0;
   out_7794323724515120914[96] = 0.0;
   out_7794323724515120914[97] = 0.0;
   out_7794323724515120914[98] = 0.0;
   out_7794323724515120914[99] = 0.0;
   out_7794323724515120914[100] = 0.0;
   out_7794323724515120914[101] = 0.0;
   out_7794323724515120914[102] = 0.0;
   out_7794323724515120914[103] = 0.0;
   out_7794323724515120914[104] = 0.0;
   out_7794323724515120914[105] = 0.0;
   out_7794323724515120914[106] = 0.0;
   out_7794323724515120914[107] = 0.0;
   out_7794323724515120914[108] = 0.0;
   out_7794323724515120914[109] = 0.0;
   out_7794323724515120914[110] = 0.0;
   out_7794323724515120914[111] = 0.0;
   out_7794323724515120914[112] = 0.0;
   out_7794323724515120914[113] = 0.0;
   out_7794323724515120914[114] = 1.0;
   out_7794323724515120914[115] = 0.0;
   out_7794323724515120914[116] = 0.0;
   out_7794323724515120914[117] = 0.0;
   out_7794323724515120914[118] = 0.0;
   out_7794323724515120914[119] = 0.0;
   out_7794323724515120914[120] = 0.0;
   out_7794323724515120914[121] = 0.0;
   out_7794323724515120914[122] = 0.0;
   out_7794323724515120914[123] = 0.0;
   out_7794323724515120914[124] = 0.0;
   out_7794323724515120914[125] = 0.0;
   out_7794323724515120914[126] = 0.0;
   out_7794323724515120914[127] = 0.0;
   out_7794323724515120914[128] = 0.0;
   out_7794323724515120914[129] = 0.0;
   out_7794323724515120914[130] = 0.0;
   out_7794323724515120914[131] = 0.0;
   out_7794323724515120914[132] = 0.0;
   out_7794323724515120914[133] = 1.0;
   out_7794323724515120914[134] = 0.0;
   out_7794323724515120914[135] = 0.0;
   out_7794323724515120914[136] = 0.0;
   out_7794323724515120914[137] = 0.0;
   out_7794323724515120914[138] = 0.0;
   out_7794323724515120914[139] = 0.0;
   out_7794323724515120914[140] = 0.0;
   out_7794323724515120914[141] = 0.0;
   out_7794323724515120914[142] = 0.0;
   out_7794323724515120914[143] = 0.0;
   out_7794323724515120914[144] = 0.0;
   out_7794323724515120914[145] = 0.0;
   out_7794323724515120914[146] = 0.0;
   out_7794323724515120914[147] = 0.0;
   out_7794323724515120914[148] = 0.0;
   out_7794323724515120914[149] = 0.0;
   out_7794323724515120914[150] = 0.0;
   out_7794323724515120914[151] = 0.0;
   out_7794323724515120914[152] = 1.0;
   out_7794323724515120914[153] = 0.0;
   out_7794323724515120914[154] = 0.0;
   out_7794323724515120914[155] = 0.0;
   out_7794323724515120914[156] = 0.0;
   out_7794323724515120914[157] = 0.0;
   out_7794323724515120914[158] = 0.0;
   out_7794323724515120914[159] = 0.0;
   out_7794323724515120914[160] = 0.0;
   out_7794323724515120914[161] = 0.0;
   out_7794323724515120914[162] = 0.0;
   out_7794323724515120914[163] = 0.0;
   out_7794323724515120914[164] = 0.0;
   out_7794323724515120914[165] = 0.0;
   out_7794323724515120914[166] = 0.0;
   out_7794323724515120914[167] = 0.0;
   out_7794323724515120914[168] = 0.0;
   out_7794323724515120914[169] = 0.0;
   out_7794323724515120914[170] = 0.0;
   out_7794323724515120914[171] = 1.0;
   out_7794323724515120914[172] = 0.0;
   out_7794323724515120914[173] = 0.0;
   out_7794323724515120914[174] = 0.0;
   out_7794323724515120914[175] = 0.0;
   out_7794323724515120914[176] = 0.0;
   out_7794323724515120914[177] = 0.0;
   out_7794323724515120914[178] = 0.0;
   out_7794323724515120914[179] = 0.0;
   out_7794323724515120914[180] = 0.0;
   out_7794323724515120914[181] = 0.0;
   out_7794323724515120914[182] = 0.0;
   out_7794323724515120914[183] = 0.0;
   out_7794323724515120914[184] = 0.0;
   out_7794323724515120914[185] = 0.0;
   out_7794323724515120914[186] = 0.0;
   out_7794323724515120914[187] = 0.0;
   out_7794323724515120914[188] = 0.0;
   out_7794323724515120914[189] = 0.0;
   out_7794323724515120914[190] = 1.0;
   out_7794323724515120914[191] = 0.0;
   out_7794323724515120914[192] = 0.0;
   out_7794323724515120914[193] = 0.0;
   out_7794323724515120914[194] = 0.0;
   out_7794323724515120914[195] = 0.0;
   out_7794323724515120914[196] = 0.0;
   out_7794323724515120914[197] = 0.0;
   out_7794323724515120914[198] = 0.0;
   out_7794323724515120914[199] = 0.0;
   out_7794323724515120914[200] = 0.0;
   out_7794323724515120914[201] = 0.0;
   out_7794323724515120914[202] = 0.0;
   out_7794323724515120914[203] = 0.0;
   out_7794323724515120914[204] = 0.0;
   out_7794323724515120914[205] = 0.0;
   out_7794323724515120914[206] = 0.0;
   out_7794323724515120914[207] = 0.0;
   out_7794323724515120914[208] = 0.0;
   out_7794323724515120914[209] = 1.0;
   out_7794323724515120914[210] = 0.0;
   out_7794323724515120914[211] = 0.0;
   out_7794323724515120914[212] = 0.0;
   out_7794323724515120914[213] = 0.0;
   out_7794323724515120914[214] = 0.0;
   out_7794323724515120914[215] = 0.0;
   out_7794323724515120914[216] = 0.0;
   out_7794323724515120914[217] = 0.0;
   out_7794323724515120914[218] = 0.0;
   out_7794323724515120914[219] = 0.0;
   out_7794323724515120914[220] = 0.0;
   out_7794323724515120914[221] = 0.0;
   out_7794323724515120914[222] = 0.0;
   out_7794323724515120914[223] = 0.0;
   out_7794323724515120914[224] = 0.0;
   out_7794323724515120914[225] = 0.0;
   out_7794323724515120914[226] = 0.0;
   out_7794323724515120914[227] = 0.0;
   out_7794323724515120914[228] = 1.0;
   out_7794323724515120914[229] = 0.0;
   out_7794323724515120914[230] = 0.0;
   out_7794323724515120914[231] = 0.0;
   out_7794323724515120914[232] = 0.0;
   out_7794323724515120914[233] = 0.0;
   out_7794323724515120914[234] = 0.0;
   out_7794323724515120914[235] = 0.0;
   out_7794323724515120914[236] = 0.0;
   out_7794323724515120914[237] = 0.0;
   out_7794323724515120914[238] = 0.0;
   out_7794323724515120914[239] = 0.0;
   out_7794323724515120914[240] = 0.0;
   out_7794323724515120914[241] = 0.0;
   out_7794323724515120914[242] = 0.0;
   out_7794323724515120914[243] = 0.0;
   out_7794323724515120914[244] = 0.0;
   out_7794323724515120914[245] = 0.0;
   out_7794323724515120914[246] = 0.0;
   out_7794323724515120914[247] = 1.0;
   out_7794323724515120914[248] = 0.0;
   out_7794323724515120914[249] = 0.0;
   out_7794323724515120914[250] = 0.0;
   out_7794323724515120914[251] = 0.0;
   out_7794323724515120914[252] = 0.0;
   out_7794323724515120914[253] = 0.0;
   out_7794323724515120914[254] = 0.0;
   out_7794323724515120914[255] = 0.0;
   out_7794323724515120914[256] = 0.0;
   out_7794323724515120914[257] = 0.0;
   out_7794323724515120914[258] = 0.0;
   out_7794323724515120914[259] = 0.0;
   out_7794323724515120914[260] = 0.0;
   out_7794323724515120914[261] = 0.0;
   out_7794323724515120914[262] = 0.0;
   out_7794323724515120914[263] = 0.0;
   out_7794323724515120914[264] = 0.0;
   out_7794323724515120914[265] = 0.0;
   out_7794323724515120914[266] = 1.0;
   out_7794323724515120914[267] = 0.0;
   out_7794323724515120914[268] = 0.0;
   out_7794323724515120914[269] = 0.0;
   out_7794323724515120914[270] = 0.0;
   out_7794323724515120914[271] = 0.0;
   out_7794323724515120914[272] = 0.0;
   out_7794323724515120914[273] = 0.0;
   out_7794323724515120914[274] = 0.0;
   out_7794323724515120914[275] = 0.0;
   out_7794323724515120914[276] = 0.0;
   out_7794323724515120914[277] = 0.0;
   out_7794323724515120914[278] = 0.0;
   out_7794323724515120914[279] = 0.0;
   out_7794323724515120914[280] = 0.0;
   out_7794323724515120914[281] = 0.0;
   out_7794323724515120914[282] = 0.0;
   out_7794323724515120914[283] = 0.0;
   out_7794323724515120914[284] = 0.0;
   out_7794323724515120914[285] = 1.0;
   out_7794323724515120914[286] = 0.0;
   out_7794323724515120914[287] = 0.0;
   out_7794323724515120914[288] = 0.0;
   out_7794323724515120914[289] = 0.0;
   out_7794323724515120914[290] = 0.0;
   out_7794323724515120914[291] = 0.0;
   out_7794323724515120914[292] = 0.0;
   out_7794323724515120914[293] = 0.0;
   out_7794323724515120914[294] = 0.0;
   out_7794323724515120914[295] = 0.0;
   out_7794323724515120914[296] = 0.0;
   out_7794323724515120914[297] = 0.0;
   out_7794323724515120914[298] = 0.0;
   out_7794323724515120914[299] = 0.0;
   out_7794323724515120914[300] = 0.0;
   out_7794323724515120914[301] = 0.0;
   out_7794323724515120914[302] = 0.0;
   out_7794323724515120914[303] = 0.0;
   out_7794323724515120914[304] = 1.0;
   out_7794323724515120914[305] = 0.0;
   out_7794323724515120914[306] = 0.0;
   out_7794323724515120914[307] = 0.0;
   out_7794323724515120914[308] = 0.0;
   out_7794323724515120914[309] = 0.0;
   out_7794323724515120914[310] = 0.0;
   out_7794323724515120914[311] = 0.0;
   out_7794323724515120914[312] = 0.0;
   out_7794323724515120914[313] = 0.0;
   out_7794323724515120914[314] = 0.0;
   out_7794323724515120914[315] = 0.0;
   out_7794323724515120914[316] = 0.0;
   out_7794323724515120914[317] = 0.0;
   out_7794323724515120914[318] = 0.0;
   out_7794323724515120914[319] = 0.0;
   out_7794323724515120914[320] = 0.0;
   out_7794323724515120914[321] = 0.0;
   out_7794323724515120914[322] = 0.0;
   out_7794323724515120914[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4407167606918814661) {
   out_4407167606918814661[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4407167606918814661[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4407167606918814661[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4407167606918814661[3] = dt*state[12] + state[3];
   out_4407167606918814661[4] = dt*state[13] + state[4];
   out_4407167606918814661[5] = dt*state[14] + state[5];
   out_4407167606918814661[6] = state[6];
   out_4407167606918814661[7] = state[7];
   out_4407167606918814661[8] = state[8];
   out_4407167606918814661[9] = state[9];
   out_4407167606918814661[10] = state[10];
   out_4407167606918814661[11] = state[11];
   out_4407167606918814661[12] = state[12];
   out_4407167606918814661[13] = state[13];
   out_4407167606918814661[14] = state[14];
   out_4407167606918814661[15] = state[15];
   out_4407167606918814661[16] = state[16];
   out_4407167606918814661[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8987983300429749257) {
   out_8987983300429749257[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8987983300429749257[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8987983300429749257[2] = 0;
   out_8987983300429749257[3] = 0;
   out_8987983300429749257[4] = 0;
   out_8987983300429749257[5] = 0;
   out_8987983300429749257[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8987983300429749257[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8987983300429749257[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8987983300429749257[9] = 0;
   out_8987983300429749257[10] = 0;
   out_8987983300429749257[11] = 0;
   out_8987983300429749257[12] = 0;
   out_8987983300429749257[13] = 0;
   out_8987983300429749257[14] = 0;
   out_8987983300429749257[15] = 0;
   out_8987983300429749257[16] = 0;
   out_8987983300429749257[17] = 0;
   out_8987983300429749257[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8987983300429749257[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8987983300429749257[20] = 0;
   out_8987983300429749257[21] = 0;
   out_8987983300429749257[22] = 0;
   out_8987983300429749257[23] = 0;
   out_8987983300429749257[24] = 0;
   out_8987983300429749257[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8987983300429749257[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8987983300429749257[27] = 0;
   out_8987983300429749257[28] = 0;
   out_8987983300429749257[29] = 0;
   out_8987983300429749257[30] = 0;
   out_8987983300429749257[31] = 0;
   out_8987983300429749257[32] = 0;
   out_8987983300429749257[33] = 0;
   out_8987983300429749257[34] = 0;
   out_8987983300429749257[35] = 0;
   out_8987983300429749257[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8987983300429749257[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8987983300429749257[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8987983300429749257[39] = 0;
   out_8987983300429749257[40] = 0;
   out_8987983300429749257[41] = 0;
   out_8987983300429749257[42] = 0;
   out_8987983300429749257[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8987983300429749257[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8987983300429749257[45] = 0;
   out_8987983300429749257[46] = 0;
   out_8987983300429749257[47] = 0;
   out_8987983300429749257[48] = 0;
   out_8987983300429749257[49] = 0;
   out_8987983300429749257[50] = 0;
   out_8987983300429749257[51] = 0;
   out_8987983300429749257[52] = 0;
   out_8987983300429749257[53] = 0;
   out_8987983300429749257[54] = 0;
   out_8987983300429749257[55] = 0;
   out_8987983300429749257[56] = 0;
   out_8987983300429749257[57] = 1;
   out_8987983300429749257[58] = 0;
   out_8987983300429749257[59] = 0;
   out_8987983300429749257[60] = 0;
   out_8987983300429749257[61] = 0;
   out_8987983300429749257[62] = 0;
   out_8987983300429749257[63] = 0;
   out_8987983300429749257[64] = 0;
   out_8987983300429749257[65] = 0;
   out_8987983300429749257[66] = dt;
   out_8987983300429749257[67] = 0;
   out_8987983300429749257[68] = 0;
   out_8987983300429749257[69] = 0;
   out_8987983300429749257[70] = 0;
   out_8987983300429749257[71] = 0;
   out_8987983300429749257[72] = 0;
   out_8987983300429749257[73] = 0;
   out_8987983300429749257[74] = 0;
   out_8987983300429749257[75] = 0;
   out_8987983300429749257[76] = 1;
   out_8987983300429749257[77] = 0;
   out_8987983300429749257[78] = 0;
   out_8987983300429749257[79] = 0;
   out_8987983300429749257[80] = 0;
   out_8987983300429749257[81] = 0;
   out_8987983300429749257[82] = 0;
   out_8987983300429749257[83] = 0;
   out_8987983300429749257[84] = 0;
   out_8987983300429749257[85] = dt;
   out_8987983300429749257[86] = 0;
   out_8987983300429749257[87] = 0;
   out_8987983300429749257[88] = 0;
   out_8987983300429749257[89] = 0;
   out_8987983300429749257[90] = 0;
   out_8987983300429749257[91] = 0;
   out_8987983300429749257[92] = 0;
   out_8987983300429749257[93] = 0;
   out_8987983300429749257[94] = 0;
   out_8987983300429749257[95] = 1;
   out_8987983300429749257[96] = 0;
   out_8987983300429749257[97] = 0;
   out_8987983300429749257[98] = 0;
   out_8987983300429749257[99] = 0;
   out_8987983300429749257[100] = 0;
   out_8987983300429749257[101] = 0;
   out_8987983300429749257[102] = 0;
   out_8987983300429749257[103] = 0;
   out_8987983300429749257[104] = dt;
   out_8987983300429749257[105] = 0;
   out_8987983300429749257[106] = 0;
   out_8987983300429749257[107] = 0;
   out_8987983300429749257[108] = 0;
   out_8987983300429749257[109] = 0;
   out_8987983300429749257[110] = 0;
   out_8987983300429749257[111] = 0;
   out_8987983300429749257[112] = 0;
   out_8987983300429749257[113] = 0;
   out_8987983300429749257[114] = 1;
   out_8987983300429749257[115] = 0;
   out_8987983300429749257[116] = 0;
   out_8987983300429749257[117] = 0;
   out_8987983300429749257[118] = 0;
   out_8987983300429749257[119] = 0;
   out_8987983300429749257[120] = 0;
   out_8987983300429749257[121] = 0;
   out_8987983300429749257[122] = 0;
   out_8987983300429749257[123] = 0;
   out_8987983300429749257[124] = 0;
   out_8987983300429749257[125] = 0;
   out_8987983300429749257[126] = 0;
   out_8987983300429749257[127] = 0;
   out_8987983300429749257[128] = 0;
   out_8987983300429749257[129] = 0;
   out_8987983300429749257[130] = 0;
   out_8987983300429749257[131] = 0;
   out_8987983300429749257[132] = 0;
   out_8987983300429749257[133] = 1;
   out_8987983300429749257[134] = 0;
   out_8987983300429749257[135] = 0;
   out_8987983300429749257[136] = 0;
   out_8987983300429749257[137] = 0;
   out_8987983300429749257[138] = 0;
   out_8987983300429749257[139] = 0;
   out_8987983300429749257[140] = 0;
   out_8987983300429749257[141] = 0;
   out_8987983300429749257[142] = 0;
   out_8987983300429749257[143] = 0;
   out_8987983300429749257[144] = 0;
   out_8987983300429749257[145] = 0;
   out_8987983300429749257[146] = 0;
   out_8987983300429749257[147] = 0;
   out_8987983300429749257[148] = 0;
   out_8987983300429749257[149] = 0;
   out_8987983300429749257[150] = 0;
   out_8987983300429749257[151] = 0;
   out_8987983300429749257[152] = 1;
   out_8987983300429749257[153] = 0;
   out_8987983300429749257[154] = 0;
   out_8987983300429749257[155] = 0;
   out_8987983300429749257[156] = 0;
   out_8987983300429749257[157] = 0;
   out_8987983300429749257[158] = 0;
   out_8987983300429749257[159] = 0;
   out_8987983300429749257[160] = 0;
   out_8987983300429749257[161] = 0;
   out_8987983300429749257[162] = 0;
   out_8987983300429749257[163] = 0;
   out_8987983300429749257[164] = 0;
   out_8987983300429749257[165] = 0;
   out_8987983300429749257[166] = 0;
   out_8987983300429749257[167] = 0;
   out_8987983300429749257[168] = 0;
   out_8987983300429749257[169] = 0;
   out_8987983300429749257[170] = 0;
   out_8987983300429749257[171] = 1;
   out_8987983300429749257[172] = 0;
   out_8987983300429749257[173] = 0;
   out_8987983300429749257[174] = 0;
   out_8987983300429749257[175] = 0;
   out_8987983300429749257[176] = 0;
   out_8987983300429749257[177] = 0;
   out_8987983300429749257[178] = 0;
   out_8987983300429749257[179] = 0;
   out_8987983300429749257[180] = 0;
   out_8987983300429749257[181] = 0;
   out_8987983300429749257[182] = 0;
   out_8987983300429749257[183] = 0;
   out_8987983300429749257[184] = 0;
   out_8987983300429749257[185] = 0;
   out_8987983300429749257[186] = 0;
   out_8987983300429749257[187] = 0;
   out_8987983300429749257[188] = 0;
   out_8987983300429749257[189] = 0;
   out_8987983300429749257[190] = 1;
   out_8987983300429749257[191] = 0;
   out_8987983300429749257[192] = 0;
   out_8987983300429749257[193] = 0;
   out_8987983300429749257[194] = 0;
   out_8987983300429749257[195] = 0;
   out_8987983300429749257[196] = 0;
   out_8987983300429749257[197] = 0;
   out_8987983300429749257[198] = 0;
   out_8987983300429749257[199] = 0;
   out_8987983300429749257[200] = 0;
   out_8987983300429749257[201] = 0;
   out_8987983300429749257[202] = 0;
   out_8987983300429749257[203] = 0;
   out_8987983300429749257[204] = 0;
   out_8987983300429749257[205] = 0;
   out_8987983300429749257[206] = 0;
   out_8987983300429749257[207] = 0;
   out_8987983300429749257[208] = 0;
   out_8987983300429749257[209] = 1;
   out_8987983300429749257[210] = 0;
   out_8987983300429749257[211] = 0;
   out_8987983300429749257[212] = 0;
   out_8987983300429749257[213] = 0;
   out_8987983300429749257[214] = 0;
   out_8987983300429749257[215] = 0;
   out_8987983300429749257[216] = 0;
   out_8987983300429749257[217] = 0;
   out_8987983300429749257[218] = 0;
   out_8987983300429749257[219] = 0;
   out_8987983300429749257[220] = 0;
   out_8987983300429749257[221] = 0;
   out_8987983300429749257[222] = 0;
   out_8987983300429749257[223] = 0;
   out_8987983300429749257[224] = 0;
   out_8987983300429749257[225] = 0;
   out_8987983300429749257[226] = 0;
   out_8987983300429749257[227] = 0;
   out_8987983300429749257[228] = 1;
   out_8987983300429749257[229] = 0;
   out_8987983300429749257[230] = 0;
   out_8987983300429749257[231] = 0;
   out_8987983300429749257[232] = 0;
   out_8987983300429749257[233] = 0;
   out_8987983300429749257[234] = 0;
   out_8987983300429749257[235] = 0;
   out_8987983300429749257[236] = 0;
   out_8987983300429749257[237] = 0;
   out_8987983300429749257[238] = 0;
   out_8987983300429749257[239] = 0;
   out_8987983300429749257[240] = 0;
   out_8987983300429749257[241] = 0;
   out_8987983300429749257[242] = 0;
   out_8987983300429749257[243] = 0;
   out_8987983300429749257[244] = 0;
   out_8987983300429749257[245] = 0;
   out_8987983300429749257[246] = 0;
   out_8987983300429749257[247] = 1;
   out_8987983300429749257[248] = 0;
   out_8987983300429749257[249] = 0;
   out_8987983300429749257[250] = 0;
   out_8987983300429749257[251] = 0;
   out_8987983300429749257[252] = 0;
   out_8987983300429749257[253] = 0;
   out_8987983300429749257[254] = 0;
   out_8987983300429749257[255] = 0;
   out_8987983300429749257[256] = 0;
   out_8987983300429749257[257] = 0;
   out_8987983300429749257[258] = 0;
   out_8987983300429749257[259] = 0;
   out_8987983300429749257[260] = 0;
   out_8987983300429749257[261] = 0;
   out_8987983300429749257[262] = 0;
   out_8987983300429749257[263] = 0;
   out_8987983300429749257[264] = 0;
   out_8987983300429749257[265] = 0;
   out_8987983300429749257[266] = 1;
   out_8987983300429749257[267] = 0;
   out_8987983300429749257[268] = 0;
   out_8987983300429749257[269] = 0;
   out_8987983300429749257[270] = 0;
   out_8987983300429749257[271] = 0;
   out_8987983300429749257[272] = 0;
   out_8987983300429749257[273] = 0;
   out_8987983300429749257[274] = 0;
   out_8987983300429749257[275] = 0;
   out_8987983300429749257[276] = 0;
   out_8987983300429749257[277] = 0;
   out_8987983300429749257[278] = 0;
   out_8987983300429749257[279] = 0;
   out_8987983300429749257[280] = 0;
   out_8987983300429749257[281] = 0;
   out_8987983300429749257[282] = 0;
   out_8987983300429749257[283] = 0;
   out_8987983300429749257[284] = 0;
   out_8987983300429749257[285] = 1;
   out_8987983300429749257[286] = 0;
   out_8987983300429749257[287] = 0;
   out_8987983300429749257[288] = 0;
   out_8987983300429749257[289] = 0;
   out_8987983300429749257[290] = 0;
   out_8987983300429749257[291] = 0;
   out_8987983300429749257[292] = 0;
   out_8987983300429749257[293] = 0;
   out_8987983300429749257[294] = 0;
   out_8987983300429749257[295] = 0;
   out_8987983300429749257[296] = 0;
   out_8987983300429749257[297] = 0;
   out_8987983300429749257[298] = 0;
   out_8987983300429749257[299] = 0;
   out_8987983300429749257[300] = 0;
   out_8987983300429749257[301] = 0;
   out_8987983300429749257[302] = 0;
   out_8987983300429749257[303] = 0;
   out_8987983300429749257[304] = 1;
   out_8987983300429749257[305] = 0;
   out_8987983300429749257[306] = 0;
   out_8987983300429749257[307] = 0;
   out_8987983300429749257[308] = 0;
   out_8987983300429749257[309] = 0;
   out_8987983300429749257[310] = 0;
   out_8987983300429749257[311] = 0;
   out_8987983300429749257[312] = 0;
   out_8987983300429749257[313] = 0;
   out_8987983300429749257[314] = 0;
   out_8987983300429749257[315] = 0;
   out_8987983300429749257[316] = 0;
   out_8987983300429749257[317] = 0;
   out_8987983300429749257[318] = 0;
   out_8987983300429749257[319] = 0;
   out_8987983300429749257[320] = 0;
   out_8987983300429749257[321] = 0;
   out_8987983300429749257[322] = 0;
   out_8987983300429749257[323] = 1;
}
void h_4(double *state, double *unused, double *out_8101504579927723665) {
   out_8101504579927723665[0] = state[6] + state[9];
   out_8101504579927723665[1] = state[7] + state[10];
   out_8101504579927723665[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1708058683136609360) {
   out_1708058683136609360[0] = 0;
   out_1708058683136609360[1] = 0;
   out_1708058683136609360[2] = 0;
   out_1708058683136609360[3] = 0;
   out_1708058683136609360[4] = 0;
   out_1708058683136609360[5] = 0;
   out_1708058683136609360[6] = 1;
   out_1708058683136609360[7] = 0;
   out_1708058683136609360[8] = 0;
   out_1708058683136609360[9] = 1;
   out_1708058683136609360[10] = 0;
   out_1708058683136609360[11] = 0;
   out_1708058683136609360[12] = 0;
   out_1708058683136609360[13] = 0;
   out_1708058683136609360[14] = 0;
   out_1708058683136609360[15] = 0;
   out_1708058683136609360[16] = 0;
   out_1708058683136609360[17] = 0;
   out_1708058683136609360[18] = 0;
   out_1708058683136609360[19] = 0;
   out_1708058683136609360[20] = 0;
   out_1708058683136609360[21] = 0;
   out_1708058683136609360[22] = 0;
   out_1708058683136609360[23] = 0;
   out_1708058683136609360[24] = 0;
   out_1708058683136609360[25] = 1;
   out_1708058683136609360[26] = 0;
   out_1708058683136609360[27] = 0;
   out_1708058683136609360[28] = 1;
   out_1708058683136609360[29] = 0;
   out_1708058683136609360[30] = 0;
   out_1708058683136609360[31] = 0;
   out_1708058683136609360[32] = 0;
   out_1708058683136609360[33] = 0;
   out_1708058683136609360[34] = 0;
   out_1708058683136609360[35] = 0;
   out_1708058683136609360[36] = 0;
   out_1708058683136609360[37] = 0;
   out_1708058683136609360[38] = 0;
   out_1708058683136609360[39] = 0;
   out_1708058683136609360[40] = 0;
   out_1708058683136609360[41] = 0;
   out_1708058683136609360[42] = 0;
   out_1708058683136609360[43] = 0;
   out_1708058683136609360[44] = 1;
   out_1708058683136609360[45] = 0;
   out_1708058683136609360[46] = 0;
   out_1708058683136609360[47] = 1;
   out_1708058683136609360[48] = 0;
   out_1708058683136609360[49] = 0;
   out_1708058683136609360[50] = 0;
   out_1708058683136609360[51] = 0;
   out_1708058683136609360[52] = 0;
   out_1708058683136609360[53] = 0;
}
void h_10(double *state, double *unused, double *out_4840518918703535700) {
   out_4840518918703535700[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4840518918703535700[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4840518918703535700[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7835481476460242475) {
   out_7835481476460242475[0] = 0;
   out_7835481476460242475[1] = 9.8100000000000005*cos(state[1]);
   out_7835481476460242475[2] = 0;
   out_7835481476460242475[3] = 0;
   out_7835481476460242475[4] = -state[8];
   out_7835481476460242475[5] = state[7];
   out_7835481476460242475[6] = 0;
   out_7835481476460242475[7] = state[5];
   out_7835481476460242475[8] = -state[4];
   out_7835481476460242475[9] = 0;
   out_7835481476460242475[10] = 0;
   out_7835481476460242475[11] = 0;
   out_7835481476460242475[12] = 1;
   out_7835481476460242475[13] = 0;
   out_7835481476460242475[14] = 0;
   out_7835481476460242475[15] = 1;
   out_7835481476460242475[16] = 0;
   out_7835481476460242475[17] = 0;
   out_7835481476460242475[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7835481476460242475[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7835481476460242475[20] = 0;
   out_7835481476460242475[21] = state[8];
   out_7835481476460242475[22] = 0;
   out_7835481476460242475[23] = -state[6];
   out_7835481476460242475[24] = -state[5];
   out_7835481476460242475[25] = 0;
   out_7835481476460242475[26] = state[3];
   out_7835481476460242475[27] = 0;
   out_7835481476460242475[28] = 0;
   out_7835481476460242475[29] = 0;
   out_7835481476460242475[30] = 0;
   out_7835481476460242475[31] = 1;
   out_7835481476460242475[32] = 0;
   out_7835481476460242475[33] = 0;
   out_7835481476460242475[34] = 1;
   out_7835481476460242475[35] = 0;
   out_7835481476460242475[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7835481476460242475[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7835481476460242475[38] = 0;
   out_7835481476460242475[39] = -state[7];
   out_7835481476460242475[40] = state[6];
   out_7835481476460242475[41] = 0;
   out_7835481476460242475[42] = state[4];
   out_7835481476460242475[43] = -state[3];
   out_7835481476460242475[44] = 0;
   out_7835481476460242475[45] = 0;
   out_7835481476460242475[46] = 0;
   out_7835481476460242475[47] = 0;
   out_7835481476460242475[48] = 0;
   out_7835481476460242475[49] = 0;
   out_7835481476460242475[50] = 1;
   out_7835481476460242475[51] = 0;
   out_7835481476460242475[52] = 0;
   out_7835481476460242475[53] = 1;
}
void h_13(double *state, double *unused, double *out_1320764634665361014) {
   out_1320764634665361014[0] = state[3];
   out_1320764634665361014[1] = state[4];
   out_1320764634665361014[2] = state[5];
}
void H_13(double *state, double *unused, double *out_9128054182256241327) {
   out_9128054182256241327[0] = 0;
   out_9128054182256241327[1] = 0;
   out_9128054182256241327[2] = 0;
   out_9128054182256241327[3] = 1;
   out_9128054182256241327[4] = 0;
   out_9128054182256241327[5] = 0;
   out_9128054182256241327[6] = 0;
   out_9128054182256241327[7] = 0;
   out_9128054182256241327[8] = 0;
   out_9128054182256241327[9] = 0;
   out_9128054182256241327[10] = 0;
   out_9128054182256241327[11] = 0;
   out_9128054182256241327[12] = 0;
   out_9128054182256241327[13] = 0;
   out_9128054182256241327[14] = 0;
   out_9128054182256241327[15] = 0;
   out_9128054182256241327[16] = 0;
   out_9128054182256241327[17] = 0;
   out_9128054182256241327[18] = 0;
   out_9128054182256241327[19] = 0;
   out_9128054182256241327[20] = 0;
   out_9128054182256241327[21] = 0;
   out_9128054182256241327[22] = 1;
   out_9128054182256241327[23] = 0;
   out_9128054182256241327[24] = 0;
   out_9128054182256241327[25] = 0;
   out_9128054182256241327[26] = 0;
   out_9128054182256241327[27] = 0;
   out_9128054182256241327[28] = 0;
   out_9128054182256241327[29] = 0;
   out_9128054182256241327[30] = 0;
   out_9128054182256241327[31] = 0;
   out_9128054182256241327[32] = 0;
   out_9128054182256241327[33] = 0;
   out_9128054182256241327[34] = 0;
   out_9128054182256241327[35] = 0;
   out_9128054182256241327[36] = 0;
   out_9128054182256241327[37] = 0;
   out_9128054182256241327[38] = 0;
   out_9128054182256241327[39] = 0;
   out_9128054182256241327[40] = 0;
   out_9128054182256241327[41] = 1;
   out_9128054182256241327[42] = 0;
   out_9128054182256241327[43] = 0;
   out_9128054182256241327[44] = 0;
   out_9128054182256241327[45] = 0;
   out_9128054182256241327[46] = 0;
   out_9128054182256241327[47] = 0;
   out_9128054182256241327[48] = 0;
   out_9128054182256241327[49] = 0;
   out_9128054182256241327[50] = 0;
   out_9128054182256241327[51] = 0;
   out_9128054182256241327[52] = 0;
   out_9128054182256241327[53] = 0;
}
void h_14(double *state, double *unused, double *out_1166377341220885334) {
   out_1166377341220885334[0] = state[6];
   out_1166377341220885334[1] = state[7];
   out_1166377341220885334[2] = state[8];
}
void H_14(double *state, double *unused, double *out_5671299539476093889) {
   out_5671299539476093889[0] = 0;
   out_5671299539476093889[1] = 0;
   out_5671299539476093889[2] = 0;
   out_5671299539476093889[3] = 0;
   out_5671299539476093889[4] = 0;
   out_5671299539476093889[5] = 0;
   out_5671299539476093889[6] = 1;
   out_5671299539476093889[7] = 0;
   out_5671299539476093889[8] = 0;
   out_5671299539476093889[9] = 0;
   out_5671299539476093889[10] = 0;
   out_5671299539476093889[11] = 0;
   out_5671299539476093889[12] = 0;
   out_5671299539476093889[13] = 0;
   out_5671299539476093889[14] = 0;
   out_5671299539476093889[15] = 0;
   out_5671299539476093889[16] = 0;
   out_5671299539476093889[17] = 0;
   out_5671299539476093889[18] = 0;
   out_5671299539476093889[19] = 0;
   out_5671299539476093889[20] = 0;
   out_5671299539476093889[21] = 0;
   out_5671299539476093889[22] = 0;
   out_5671299539476093889[23] = 0;
   out_5671299539476093889[24] = 0;
   out_5671299539476093889[25] = 1;
   out_5671299539476093889[26] = 0;
   out_5671299539476093889[27] = 0;
   out_5671299539476093889[28] = 0;
   out_5671299539476093889[29] = 0;
   out_5671299539476093889[30] = 0;
   out_5671299539476093889[31] = 0;
   out_5671299539476093889[32] = 0;
   out_5671299539476093889[33] = 0;
   out_5671299539476093889[34] = 0;
   out_5671299539476093889[35] = 0;
   out_5671299539476093889[36] = 0;
   out_5671299539476093889[37] = 0;
   out_5671299539476093889[38] = 0;
   out_5671299539476093889[39] = 0;
   out_5671299539476093889[40] = 0;
   out_5671299539476093889[41] = 0;
   out_5671299539476093889[42] = 0;
   out_5671299539476093889[43] = 0;
   out_5671299539476093889[44] = 1;
   out_5671299539476093889[45] = 0;
   out_5671299539476093889[46] = 0;
   out_5671299539476093889[47] = 0;
   out_5671299539476093889[48] = 0;
   out_5671299539476093889[49] = 0;
   out_5671299539476093889[50] = 0;
   out_5671299539476093889[51] = 0;
   out_5671299539476093889[52] = 0;
   out_5671299539476093889[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4597586283991589707) {
  err_fun(nom_x, delta_x, out_4597586283991589707);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2969881635711261724) {
  inv_err_fun(nom_x, true_x, out_2969881635711261724);
}
void pose_H_mod_fun(double *state, double *out_7794323724515120914) {
  H_mod_fun(state, out_7794323724515120914);
}
void pose_f_fun(double *state, double dt, double *out_4407167606918814661) {
  f_fun(state,  dt, out_4407167606918814661);
}
void pose_F_fun(double *state, double dt, double *out_8987983300429749257) {
  F_fun(state,  dt, out_8987983300429749257);
}
void pose_h_4(double *state, double *unused, double *out_8101504579927723665) {
  h_4(state, unused, out_8101504579927723665);
}
void pose_H_4(double *state, double *unused, double *out_1708058683136609360) {
  H_4(state, unused, out_1708058683136609360);
}
void pose_h_10(double *state, double *unused, double *out_4840518918703535700) {
  h_10(state, unused, out_4840518918703535700);
}
void pose_H_10(double *state, double *unused, double *out_7835481476460242475) {
  H_10(state, unused, out_7835481476460242475);
}
void pose_h_13(double *state, double *unused, double *out_1320764634665361014) {
  h_13(state, unused, out_1320764634665361014);
}
void pose_H_13(double *state, double *unused, double *out_9128054182256241327) {
  H_13(state, unused, out_9128054182256241327);
}
void pose_h_14(double *state, double *unused, double *out_1166377341220885334) {
  h_14(state, unused, out_1166377341220885334);
}
void pose_H_14(double *state, double *unused, double *out_5671299539476093889) {
  H_14(state, unused, out_5671299539476093889);
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
