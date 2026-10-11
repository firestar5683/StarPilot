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
void err_fun(double *nom_x, double *delta_x, double *out_2903893253895971355) {
   out_2903893253895971355[0] = delta_x[0] + nom_x[0];
   out_2903893253895971355[1] = delta_x[1] + nom_x[1];
   out_2903893253895971355[2] = delta_x[2] + nom_x[2];
   out_2903893253895971355[3] = delta_x[3] + nom_x[3];
   out_2903893253895971355[4] = delta_x[4] + nom_x[4];
   out_2903893253895971355[5] = delta_x[5] + nom_x[5];
   out_2903893253895971355[6] = delta_x[6] + nom_x[6];
   out_2903893253895971355[7] = delta_x[7] + nom_x[7];
   out_2903893253895971355[8] = delta_x[8] + nom_x[8];
   out_2903893253895971355[9] = delta_x[9] + nom_x[9];
   out_2903893253895971355[10] = delta_x[10] + nom_x[10];
   out_2903893253895971355[11] = delta_x[11] + nom_x[11];
   out_2903893253895971355[12] = delta_x[12] + nom_x[12];
   out_2903893253895971355[13] = delta_x[13] + nom_x[13];
   out_2903893253895971355[14] = delta_x[14] + nom_x[14];
   out_2903893253895971355[15] = delta_x[15] + nom_x[15];
   out_2903893253895971355[16] = delta_x[16] + nom_x[16];
   out_2903893253895971355[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3928278332152438487) {
   out_3928278332152438487[0] = -nom_x[0] + true_x[0];
   out_3928278332152438487[1] = -nom_x[1] + true_x[1];
   out_3928278332152438487[2] = -nom_x[2] + true_x[2];
   out_3928278332152438487[3] = -nom_x[3] + true_x[3];
   out_3928278332152438487[4] = -nom_x[4] + true_x[4];
   out_3928278332152438487[5] = -nom_x[5] + true_x[5];
   out_3928278332152438487[6] = -nom_x[6] + true_x[6];
   out_3928278332152438487[7] = -nom_x[7] + true_x[7];
   out_3928278332152438487[8] = -nom_x[8] + true_x[8];
   out_3928278332152438487[9] = -nom_x[9] + true_x[9];
   out_3928278332152438487[10] = -nom_x[10] + true_x[10];
   out_3928278332152438487[11] = -nom_x[11] + true_x[11];
   out_3928278332152438487[12] = -nom_x[12] + true_x[12];
   out_3928278332152438487[13] = -nom_x[13] + true_x[13];
   out_3928278332152438487[14] = -nom_x[14] + true_x[14];
   out_3928278332152438487[15] = -nom_x[15] + true_x[15];
   out_3928278332152438487[16] = -nom_x[16] + true_x[16];
   out_3928278332152438487[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5666984403538513454) {
   out_5666984403538513454[0] = 1.0;
   out_5666984403538513454[1] = 0.0;
   out_5666984403538513454[2] = 0.0;
   out_5666984403538513454[3] = 0.0;
   out_5666984403538513454[4] = 0.0;
   out_5666984403538513454[5] = 0.0;
   out_5666984403538513454[6] = 0.0;
   out_5666984403538513454[7] = 0.0;
   out_5666984403538513454[8] = 0.0;
   out_5666984403538513454[9] = 0.0;
   out_5666984403538513454[10] = 0.0;
   out_5666984403538513454[11] = 0.0;
   out_5666984403538513454[12] = 0.0;
   out_5666984403538513454[13] = 0.0;
   out_5666984403538513454[14] = 0.0;
   out_5666984403538513454[15] = 0.0;
   out_5666984403538513454[16] = 0.0;
   out_5666984403538513454[17] = 0.0;
   out_5666984403538513454[18] = 0.0;
   out_5666984403538513454[19] = 1.0;
   out_5666984403538513454[20] = 0.0;
   out_5666984403538513454[21] = 0.0;
   out_5666984403538513454[22] = 0.0;
   out_5666984403538513454[23] = 0.0;
   out_5666984403538513454[24] = 0.0;
   out_5666984403538513454[25] = 0.0;
   out_5666984403538513454[26] = 0.0;
   out_5666984403538513454[27] = 0.0;
   out_5666984403538513454[28] = 0.0;
   out_5666984403538513454[29] = 0.0;
   out_5666984403538513454[30] = 0.0;
   out_5666984403538513454[31] = 0.0;
   out_5666984403538513454[32] = 0.0;
   out_5666984403538513454[33] = 0.0;
   out_5666984403538513454[34] = 0.0;
   out_5666984403538513454[35] = 0.0;
   out_5666984403538513454[36] = 0.0;
   out_5666984403538513454[37] = 0.0;
   out_5666984403538513454[38] = 1.0;
   out_5666984403538513454[39] = 0.0;
   out_5666984403538513454[40] = 0.0;
   out_5666984403538513454[41] = 0.0;
   out_5666984403538513454[42] = 0.0;
   out_5666984403538513454[43] = 0.0;
   out_5666984403538513454[44] = 0.0;
   out_5666984403538513454[45] = 0.0;
   out_5666984403538513454[46] = 0.0;
   out_5666984403538513454[47] = 0.0;
   out_5666984403538513454[48] = 0.0;
   out_5666984403538513454[49] = 0.0;
   out_5666984403538513454[50] = 0.0;
   out_5666984403538513454[51] = 0.0;
   out_5666984403538513454[52] = 0.0;
   out_5666984403538513454[53] = 0.0;
   out_5666984403538513454[54] = 0.0;
   out_5666984403538513454[55] = 0.0;
   out_5666984403538513454[56] = 0.0;
   out_5666984403538513454[57] = 1.0;
   out_5666984403538513454[58] = 0.0;
   out_5666984403538513454[59] = 0.0;
   out_5666984403538513454[60] = 0.0;
   out_5666984403538513454[61] = 0.0;
   out_5666984403538513454[62] = 0.0;
   out_5666984403538513454[63] = 0.0;
   out_5666984403538513454[64] = 0.0;
   out_5666984403538513454[65] = 0.0;
   out_5666984403538513454[66] = 0.0;
   out_5666984403538513454[67] = 0.0;
   out_5666984403538513454[68] = 0.0;
   out_5666984403538513454[69] = 0.0;
   out_5666984403538513454[70] = 0.0;
   out_5666984403538513454[71] = 0.0;
   out_5666984403538513454[72] = 0.0;
   out_5666984403538513454[73] = 0.0;
   out_5666984403538513454[74] = 0.0;
   out_5666984403538513454[75] = 0.0;
   out_5666984403538513454[76] = 1.0;
   out_5666984403538513454[77] = 0.0;
   out_5666984403538513454[78] = 0.0;
   out_5666984403538513454[79] = 0.0;
   out_5666984403538513454[80] = 0.0;
   out_5666984403538513454[81] = 0.0;
   out_5666984403538513454[82] = 0.0;
   out_5666984403538513454[83] = 0.0;
   out_5666984403538513454[84] = 0.0;
   out_5666984403538513454[85] = 0.0;
   out_5666984403538513454[86] = 0.0;
   out_5666984403538513454[87] = 0.0;
   out_5666984403538513454[88] = 0.0;
   out_5666984403538513454[89] = 0.0;
   out_5666984403538513454[90] = 0.0;
   out_5666984403538513454[91] = 0.0;
   out_5666984403538513454[92] = 0.0;
   out_5666984403538513454[93] = 0.0;
   out_5666984403538513454[94] = 0.0;
   out_5666984403538513454[95] = 1.0;
   out_5666984403538513454[96] = 0.0;
   out_5666984403538513454[97] = 0.0;
   out_5666984403538513454[98] = 0.0;
   out_5666984403538513454[99] = 0.0;
   out_5666984403538513454[100] = 0.0;
   out_5666984403538513454[101] = 0.0;
   out_5666984403538513454[102] = 0.0;
   out_5666984403538513454[103] = 0.0;
   out_5666984403538513454[104] = 0.0;
   out_5666984403538513454[105] = 0.0;
   out_5666984403538513454[106] = 0.0;
   out_5666984403538513454[107] = 0.0;
   out_5666984403538513454[108] = 0.0;
   out_5666984403538513454[109] = 0.0;
   out_5666984403538513454[110] = 0.0;
   out_5666984403538513454[111] = 0.0;
   out_5666984403538513454[112] = 0.0;
   out_5666984403538513454[113] = 0.0;
   out_5666984403538513454[114] = 1.0;
   out_5666984403538513454[115] = 0.0;
   out_5666984403538513454[116] = 0.0;
   out_5666984403538513454[117] = 0.0;
   out_5666984403538513454[118] = 0.0;
   out_5666984403538513454[119] = 0.0;
   out_5666984403538513454[120] = 0.0;
   out_5666984403538513454[121] = 0.0;
   out_5666984403538513454[122] = 0.0;
   out_5666984403538513454[123] = 0.0;
   out_5666984403538513454[124] = 0.0;
   out_5666984403538513454[125] = 0.0;
   out_5666984403538513454[126] = 0.0;
   out_5666984403538513454[127] = 0.0;
   out_5666984403538513454[128] = 0.0;
   out_5666984403538513454[129] = 0.0;
   out_5666984403538513454[130] = 0.0;
   out_5666984403538513454[131] = 0.0;
   out_5666984403538513454[132] = 0.0;
   out_5666984403538513454[133] = 1.0;
   out_5666984403538513454[134] = 0.0;
   out_5666984403538513454[135] = 0.0;
   out_5666984403538513454[136] = 0.0;
   out_5666984403538513454[137] = 0.0;
   out_5666984403538513454[138] = 0.0;
   out_5666984403538513454[139] = 0.0;
   out_5666984403538513454[140] = 0.0;
   out_5666984403538513454[141] = 0.0;
   out_5666984403538513454[142] = 0.0;
   out_5666984403538513454[143] = 0.0;
   out_5666984403538513454[144] = 0.0;
   out_5666984403538513454[145] = 0.0;
   out_5666984403538513454[146] = 0.0;
   out_5666984403538513454[147] = 0.0;
   out_5666984403538513454[148] = 0.0;
   out_5666984403538513454[149] = 0.0;
   out_5666984403538513454[150] = 0.0;
   out_5666984403538513454[151] = 0.0;
   out_5666984403538513454[152] = 1.0;
   out_5666984403538513454[153] = 0.0;
   out_5666984403538513454[154] = 0.0;
   out_5666984403538513454[155] = 0.0;
   out_5666984403538513454[156] = 0.0;
   out_5666984403538513454[157] = 0.0;
   out_5666984403538513454[158] = 0.0;
   out_5666984403538513454[159] = 0.0;
   out_5666984403538513454[160] = 0.0;
   out_5666984403538513454[161] = 0.0;
   out_5666984403538513454[162] = 0.0;
   out_5666984403538513454[163] = 0.0;
   out_5666984403538513454[164] = 0.0;
   out_5666984403538513454[165] = 0.0;
   out_5666984403538513454[166] = 0.0;
   out_5666984403538513454[167] = 0.0;
   out_5666984403538513454[168] = 0.0;
   out_5666984403538513454[169] = 0.0;
   out_5666984403538513454[170] = 0.0;
   out_5666984403538513454[171] = 1.0;
   out_5666984403538513454[172] = 0.0;
   out_5666984403538513454[173] = 0.0;
   out_5666984403538513454[174] = 0.0;
   out_5666984403538513454[175] = 0.0;
   out_5666984403538513454[176] = 0.0;
   out_5666984403538513454[177] = 0.0;
   out_5666984403538513454[178] = 0.0;
   out_5666984403538513454[179] = 0.0;
   out_5666984403538513454[180] = 0.0;
   out_5666984403538513454[181] = 0.0;
   out_5666984403538513454[182] = 0.0;
   out_5666984403538513454[183] = 0.0;
   out_5666984403538513454[184] = 0.0;
   out_5666984403538513454[185] = 0.0;
   out_5666984403538513454[186] = 0.0;
   out_5666984403538513454[187] = 0.0;
   out_5666984403538513454[188] = 0.0;
   out_5666984403538513454[189] = 0.0;
   out_5666984403538513454[190] = 1.0;
   out_5666984403538513454[191] = 0.0;
   out_5666984403538513454[192] = 0.0;
   out_5666984403538513454[193] = 0.0;
   out_5666984403538513454[194] = 0.0;
   out_5666984403538513454[195] = 0.0;
   out_5666984403538513454[196] = 0.0;
   out_5666984403538513454[197] = 0.0;
   out_5666984403538513454[198] = 0.0;
   out_5666984403538513454[199] = 0.0;
   out_5666984403538513454[200] = 0.0;
   out_5666984403538513454[201] = 0.0;
   out_5666984403538513454[202] = 0.0;
   out_5666984403538513454[203] = 0.0;
   out_5666984403538513454[204] = 0.0;
   out_5666984403538513454[205] = 0.0;
   out_5666984403538513454[206] = 0.0;
   out_5666984403538513454[207] = 0.0;
   out_5666984403538513454[208] = 0.0;
   out_5666984403538513454[209] = 1.0;
   out_5666984403538513454[210] = 0.0;
   out_5666984403538513454[211] = 0.0;
   out_5666984403538513454[212] = 0.0;
   out_5666984403538513454[213] = 0.0;
   out_5666984403538513454[214] = 0.0;
   out_5666984403538513454[215] = 0.0;
   out_5666984403538513454[216] = 0.0;
   out_5666984403538513454[217] = 0.0;
   out_5666984403538513454[218] = 0.0;
   out_5666984403538513454[219] = 0.0;
   out_5666984403538513454[220] = 0.0;
   out_5666984403538513454[221] = 0.0;
   out_5666984403538513454[222] = 0.0;
   out_5666984403538513454[223] = 0.0;
   out_5666984403538513454[224] = 0.0;
   out_5666984403538513454[225] = 0.0;
   out_5666984403538513454[226] = 0.0;
   out_5666984403538513454[227] = 0.0;
   out_5666984403538513454[228] = 1.0;
   out_5666984403538513454[229] = 0.0;
   out_5666984403538513454[230] = 0.0;
   out_5666984403538513454[231] = 0.0;
   out_5666984403538513454[232] = 0.0;
   out_5666984403538513454[233] = 0.0;
   out_5666984403538513454[234] = 0.0;
   out_5666984403538513454[235] = 0.0;
   out_5666984403538513454[236] = 0.0;
   out_5666984403538513454[237] = 0.0;
   out_5666984403538513454[238] = 0.0;
   out_5666984403538513454[239] = 0.0;
   out_5666984403538513454[240] = 0.0;
   out_5666984403538513454[241] = 0.0;
   out_5666984403538513454[242] = 0.0;
   out_5666984403538513454[243] = 0.0;
   out_5666984403538513454[244] = 0.0;
   out_5666984403538513454[245] = 0.0;
   out_5666984403538513454[246] = 0.0;
   out_5666984403538513454[247] = 1.0;
   out_5666984403538513454[248] = 0.0;
   out_5666984403538513454[249] = 0.0;
   out_5666984403538513454[250] = 0.0;
   out_5666984403538513454[251] = 0.0;
   out_5666984403538513454[252] = 0.0;
   out_5666984403538513454[253] = 0.0;
   out_5666984403538513454[254] = 0.0;
   out_5666984403538513454[255] = 0.0;
   out_5666984403538513454[256] = 0.0;
   out_5666984403538513454[257] = 0.0;
   out_5666984403538513454[258] = 0.0;
   out_5666984403538513454[259] = 0.0;
   out_5666984403538513454[260] = 0.0;
   out_5666984403538513454[261] = 0.0;
   out_5666984403538513454[262] = 0.0;
   out_5666984403538513454[263] = 0.0;
   out_5666984403538513454[264] = 0.0;
   out_5666984403538513454[265] = 0.0;
   out_5666984403538513454[266] = 1.0;
   out_5666984403538513454[267] = 0.0;
   out_5666984403538513454[268] = 0.0;
   out_5666984403538513454[269] = 0.0;
   out_5666984403538513454[270] = 0.0;
   out_5666984403538513454[271] = 0.0;
   out_5666984403538513454[272] = 0.0;
   out_5666984403538513454[273] = 0.0;
   out_5666984403538513454[274] = 0.0;
   out_5666984403538513454[275] = 0.0;
   out_5666984403538513454[276] = 0.0;
   out_5666984403538513454[277] = 0.0;
   out_5666984403538513454[278] = 0.0;
   out_5666984403538513454[279] = 0.0;
   out_5666984403538513454[280] = 0.0;
   out_5666984403538513454[281] = 0.0;
   out_5666984403538513454[282] = 0.0;
   out_5666984403538513454[283] = 0.0;
   out_5666984403538513454[284] = 0.0;
   out_5666984403538513454[285] = 1.0;
   out_5666984403538513454[286] = 0.0;
   out_5666984403538513454[287] = 0.0;
   out_5666984403538513454[288] = 0.0;
   out_5666984403538513454[289] = 0.0;
   out_5666984403538513454[290] = 0.0;
   out_5666984403538513454[291] = 0.0;
   out_5666984403538513454[292] = 0.0;
   out_5666984403538513454[293] = 0.0;
   out_5666984403538513454[294] = 0.0;
   out_5666984403538513454[295] = 0.0;
   out_5666984403538513454[296] = 0.0;
   out_5666984403538513454[297] = 0.0;
   out_5666984403538513454[298] = 0.0;
   out_5666984403538513454[299] = 0.0;
   out_5666984403538513454[300] = 0.0;
   out_5666984403538513454[301] = 0.0;
   out_5666984403538513454[302] = 0.0;
   out_5666984403538513454[303] = 0.0;
   out_5666984403538513454[304] = 1.0;
   out_5666984403538513454[305] = 0.0;
   out_5666984403538513454[306] = 0.0;
   out_5666984403538513454[307] = 0.0;
   out_5666984403538513454[308] = 0.0;
   out_5666984403538513454[309] = 0.0;
   out_5666984403538513454[310] = 0.0;
   out_5666984403538513454[311] = 0.0;
   out_5666984403538513454[312] = 0.0;
   out_5666984403538513454[313] = 0.0;
   out_5666984403538513454[314] = 0.0;
   out_5666984403538513454[315] = 0.0;
   out_5666984403538513454[316] = 0.0;
   out_5666984403538513454[317] = 0.0;
   out_5666984403538513454[318] = 0.0;
   out_5666984403538513454[319] = 0.0;
   out_5666984403538513454[320] = 0.0;
   out_5666984403538513454[321] = 0.0;
   out_5666984403538513454[322] = 0.0;
   out_5666984403538513454[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3108653889513613454) {
   out_3108653889513613454[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3108653889513613454[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3108653889513613454[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3108653889513613454[3] = dt*state[12] + state[3];
   out_3108653889513613454[4] = dt*state[13] + state[4];
   out_3108653889513613454[5] = dt*state[14] + state[5];
   out_3108653889513613454[6] = state[6];
   out_3108653889513613454[7] = state[7];
   out_3108653889513613454[8] = state[8];
   out_3108653889513613454[9] = state[9];
   out_3108653889513613454[10] = state[10];
   out_3108653889513613454[11] = state[11];
   out_3108653889513613454[12] = state[12];
   out_3108653889513613454[13] = state[13];
   out_3108653889513613454[14] = state[14];
   out_3108653889513613454[15] = state[15];
   out_3108653889513613454[16] = state[16];
   out_3108653889513613454[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3156103136607478463) {
   out_3156103136607478463[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3156103136607478463[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3156103136607478463[2] = 0;
   out_3156103136607478463[3] = 0;
   out_3156103136607478463[4] = 0;
   out_3156103136607478463[5] = 0;
   out_3156103136607478463[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3156103136607478463[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3156103136607478463[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3156103136607478463[9] = 0;
   out_3156103136607478463[10] = 0;
   out_3156103136607478463[11] = 0;
   out_3156103136607478463[12] = 0;
   out_3156103136607478463[13] = 0;
   out_3156103136607478463[14] = 0;
   out_3156103136607478463[15] = 0;
   out_3156103136607478463[16] = 0;
   out_3156103136607478463[17] = 0;
   out_3156103136607478463[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3156103136607478463[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3156103136607478463[20] = 0;
   out_3156103136607478463[21] = 0;
   out_3156103136607478463[22] = 0;
   out_3156103136607478463[23] = 0;
   out_3156103136607478463[24] = 0;
   out_3156103136607478463[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3156103136607478463[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3156103136607478463[27] = 0;
   out_3156103136607478463[28] = 0;
   out_3156103136607478463[29] = 0;
   out_3156103136607478463[30] = 0;
   out_3156103136607478463[31] = 0;
   out_3156103136607478463[32] = 0;
   out_3156103136607478463[33] = 0;
   out_3156103136607478463[34] = 0;
   out_3156103136607478463[35] = 0;
   out_3156103136607478463[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3156103136607478463[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3156103136607478463[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3156103136607478463[39] = 0;
   out_3156103136607478463[40] = 0;
   out_3156103136607478463[41] = 0;
   out_3156103136607478463[42] = 0;
   out_3156103136607478463[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3156103136607478463[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3156103136607478463[45] = 0;
   out_3156103136607478463[46] = 0;
   out_3156103136607478463[47] = 0;
   out_3156103136607478463[48] = 0;
   out_3156103136607478463[49] = 0;
   out_3156103136607478463[50] = 0;
   out_3156103136607478463[51] = 0;
   out_3156103136607478463[52] = 0;
   out_3156103136607478463[53] = 0;
   out_3156103136607478463[54] = 0;
   out_3156103136607478463[55] = 0;
   out_3156103136607478463[56] = 0;
   out_3156103136607478463[57] = 1;
   out_3156103136607478463[58] = 0;
   out_3156103136607478463[59] = 0;
   out_3156103136607478463[60] = 0;
   out_3156103136607478463[61] = 0;
   out_3156103136607478463[62] = 0;
   out_3156103136607478463[63] = 0;
   out_3156103136607478463[64] = 0;
   out_3156103136607478463[65] = 0;
   out_3156103136607478463[66] = dt;
   out_3156103136607478463[67] = 0;
   out_3156103136607478463[68] = 0;
   out_3156103136607478463[69] = 0;
   out_3156103136607478463[70] = 0;
   out_3156103136607478463[71] = 0;
   out_3156103136607478463[72] = 0;
   out_3156103136607478463[73] = 0;
   out_3156103136607478463[74] = 0;
   out_3156103136607478463[75] = 0;
   out_3156103136607478463[76] = 1;
   out_3156103136607478463[77] = 0;
   out_3156103136607478463[78] = 0;
   out_3156103136607478463[79] = 0;
   out_3156103136607478463[80] = 0;
   out_3156103136607478463[81] = 0;
   out_3156103136607478463[82] = 0;
   out_3156103136607478463[83] = 0;
   out_3156103136607478463[84] = 0;
   out_3156103136607478463[85] = dt;
   out_3156103136607478463[86] = 0;
   out_3156103136607478463[87] = 0;
   out_3156103136607478463[88] = 0;
   out_3156103136607478463[89] = 0;
   out_3156103136607478463[90] = 0;
   out_3156103136607478463[91] = 0;
   out_3156103136607478463[92] = 0;
   out_3156103136607478463[93] = 0;
   out_3156103136607478463[94] = 0;
   out_3156103136607478463[95] = 1;
   out_3156103136607478463[96] = 0;
   out_3156103136607478463[97] = 0;
   out_3156103136607478463[98] = 0;
   out_3156103136607478463[99] = 0;
   out_3156103136607478463[100] = 0;
   out_3156103136607478463[101] = 0;
   out_3156103136607478463[102] = 0;
   out_3156103136607478463[103] = 0;
   out_3156103136607478463[104] = dt;
   out_3156103136607478463[105] = 0;
   out_3156103136607478463[106] = 0;
   out_3156103136607478463[107] = 0;
   out_3156103136607478463[108] = 0;
   out_3156103136607478463[109] = 0;
   out_3156103136607478463[110] = 0;
   out_3156103136607478463[111] = 0;
   out_3156103136607478463[112] = 0;
   out_3156103136607478463[113] = 0;
   out_3156103136607478463[114] = 1;
   out_3156103136607478463[115] = 0;
   out_3156103136607478463[116] = 0;
   out_3156103136607478463[117] = 0;
   out_3156103136607478463[118] = 0;
   out_3156103136607478463[119] = 0;
   out_3156103136607478463[120] = 0;
   out_3156103136607478463[121] = 0;
   out_3156103136607478463[122] = 0;
   out_3156103136607478463[123] = 0;
   out_3156103136607478463[124] = 0;
   out_3156103136607478463[125] = 0;
   out_3156103136607478463[126] = 0;
   out_3156103136607478463[127] = 0;
   out_3156103136607478463[128] = 0;
   out_3156103136607478463[129] = 0;
   out_3156103136607478463[130] = 0;
   out_3156103136607478463[131] = 0;
   out_3156103136607478463[132] = 0;
   out_3156103136607478463[133] = 1;
   out_3156103136607478463[134] = 0;
   out_3156103136607478463[135] = 0;
   out_3156103136607478463[136] = 0;
   out_3156103136607478463[137] = 0;
   out_3156103136607478463[138] = 0;
   out_3156103136607478463[139] = 0;
   out_3156103136607478463[140] = 0;
   out_3156103136607478463[141] = 0;
   out_3156103136607478463[142] = 0;
   out_3156103136607478463[143] = 0;
   out_3156103136607478463[144] = 0;
   out_3156103136607478463[145] = 0;
   out_3156103136607478463[146] = 0;
   out_3156103136607478463[147] = 0;
   out_3156103136607478463[148] = 0;
   out_3156103136607478463[149] = 0;
   out_3156103136607478463[150] = 0;
   out_3156103136607478463[151] = 0;
   out_3156103136607478463[152] = 1;
   out_3156103136607478463[153] = 0;
   out_3156103136607478463[154] = 0;
   out_3156103136607478463[155] = 0;
   out_3156103136607478463[156] = 0;
   out_3156103136607478463[157] = 0;
   out_3156103136607478463[158] = 0;
   out_3156103136607478463[159] = 0;
   out_3156103136607478463[160] = 0;
   out_3156103136607478463[161] = 0;
   out_3156103136607478463[162] = 0;
   out_3156103136607478463[163] = 0;
   out_3156103136607478463[164] = 0;
   out_3156103136607478463[165] = 0;
   out_3156103136607478463[166] = 0;
   out_3156103136607478463[167] = 0;
   out_3156103136607478463[168] = 0;
   out_3156103136607478463[169] = 0;
   out_3156103136607478463[170] = 0;
   out_3156103136607478463[171] = 1;
   out_3156103136607478463[172] = 0;
   out_3156103136607478463[173] = 0;
   out_3156103136607478463[174] = 0;
   out_3156103136607478463[175] = 0;
   out_3156103136607478463[176] = 0;
   out_3156103136607478463[177] = 0;
   out_3156103136607478463[178] = 0;
   out_3156103136607478463[179] = 0;
   out_3156103136607478463[180] = 0;
   out_3156103136607478463[181] = 0;
   out_3156103136607478463[182] = 0;
   out_3156103136607478463[183] = 0;
   out_3156103136607478463[184] = 0;
   out_3156103136607478463[185] = 0;
   out_3156103136607478463[186] = 0;
   out_3156103136607478463[187] = 0;
   out_3156103136607478463[188] = 0;
   out_3156103136607478463[189] = 0;
   out_3156103136607478463[190] = 1;
   out_3156103136607478463[191] = 0;
   out_3156103136607478463[192] = 0;
   out_3156103136607478463[193] = 0;
   out_3156103136607478463[194] = 0;
   out_3156103136607478463[195] = 0;
   out_3156103136607478463[196] = 0;
   out_3156103136607478463[197] = 0;
   out_3156103136607478463[198] = 0;
   out_3156103136607478463[199] = 0;
   out_3156103136607478463[200] = 0;
   out_3156103136607478463[201] = 0;
   out_3156103136607478463[202] = 0;
   out_3156103136607478463[203] = 0;
   out_3156103136607478463[204] = 0;
   out_3156103136607478463[205] = 0;
   out_3156103136607478463[206] = 0;
   out_3156103136607478463[207] = 0;
   out_3156103136607478463[208] = 0;
   out_3156103136607478463[209] = 1;
   out_3156103136607478463[210] = 0;
   out_3156103136607478463[211] = 0;
   out_3156103136607478463[212] = 0;
   out_3156103136607478463[213] = 0;
   out_3156103136607478463[214] = 0;
   out_3156103136607478463[215] = 0;
   out_3156103136607478463[216] = 0;
   out_3156103136607478463[217] = 0;
   out_3156103136607478463[218] = 0;
   out_3156103136607478463[219] = 0;
   out_3156103136607478463[220] = 0;
   out_3156103136607478463[221] = 0;
   out_3156103136607478463[222] = 0;
   out_3156103136607478463[223] = 0;
   out_3156103136607478463[224] = 0;
   out_3156103136607478463[225] = 0;
   out_3156103136607478463[226] = 0;
   out_3156103136607478463[227] = 0;
   out_3156103136607478463[228] = 1;
   out_3156103136607478463[229] = 0;
   out_3156103136607478463[230] = 0;
   out_3156103136607478463[231] = 0;
   out_3156103136607478463[232] = 0;
   out_3156103136607478463[233] = 0;
   out_3156103136607478463[234] = 0;
   out_3156103136607478463[235] = 0;
   out_3156103136607478463[236] = 0;
   out_3156103136607478463[237] = 0;
   out_3156103136607478463[238] = 0;
   out_3156103136607478463[239] = 0;
   out_3156103136607478463[240] = 0;
   out_3156103136607478463[241] = 0;
   out_3156103136607478463[242] = 0;
   out_3156103136607478463[243] = 0;
   out_3156103136607478463[244] = 0;
   out_3156103136607478463[245] = 0;
   out_3156103136607478463[246] = 0;
   out_3156103136607478463[247] = 1;
   out_3156103136607478463[248] = 0;
   out_3156103136607478463[249] = 0;
   out_3156103136607478463[250] = 0;
   out_3156103136607478463[251] = 0;
   out_3156103136607478463[252] = 0;
   out_3156103136607478463[253] = 0;
   out_3156103136607478463[254] = 0;
   out_3156103136607478463[255] = 0;
   out_3156103136607478463[256] = 0;
   out_3156103136607478463[257] = 0;
   out_3156103136607478463[258] = 0;
   out_3156103136607478463[259] = 0;
   out_3156103136607478463[260] = 0;
   out_3156103136607478463[261] = 0;
   out_3156103136607478463[262] = 0;
   out_3156103136607478463[263] = 0;
   out_3156103136607478463[264] = 0;
   out_3156103136607478463[265] = 0;
   out_3156103136607478463[266] = 1;
   out_3156103136607478463[267] = 0;
   out_3156103136607478463[268] = 0;
   out_3156103136607478463[269] = 0;
   out_3156103136607478463[270] = 0;
   out_3156103136607478463[271] = 0;
   out_3156103136607478463[272] = 0;
   out_3156103136607478463[273] = 0;
   out_3156103136607478463[274] = 0;
   out_3156103136607478463[275] = 0;
   out_3156103136607478463[276] = 0;
   out_3156103136607478463[277] = 0;
   out_3156103136607478463[278] = 0;
   out_3156103136607478463[279] = 0;
   out_3156103136607478463[280] = 0;
   out_3156103136607478463[281] = 0;
   out_3156103136607478463[282] = 0;
   out_3156103136607478463[283] = 0;
   out_3156103136607478463[284] = 0;
   out_3156103136607478463[285] = 1;
   out_3156103136607478463[286] = 0;
   out_3156103136607478463[287] = 0;
   out_3156103136607478463[288] = 0;
   out_3156103136607478463[289] = 0;
   out_3156103136607478463[290] = 0;
   out_3156103136607478463[291] = 0;
   out_3156103136607478463[292] = 0;
   out_3156103136607478463[293] = 0;
   out_3156103136607478463[294] = 0;
   out_3156103136607478463[295] = 0;
   out_3156103136607478463[296] = 0;
   out_3156103136607478463[297] = 0;
   out_3156103136607478463[298] = 0;
   out_3156103136607478463[299] = 0;
   out_3156103136607478463[300] = 0;
   out_3156103136607478463[301] = 0;
   out_3156103136607478463[302] = 0;
   out_3156103136607478463[303] = 0;
   out_3156103136607478463[304] = 1;
   out_3156103136607478463[305] = 0;
   out_3156103136607478463[306] = 0;
   out_3156103136607478463[307] = 0;
   out_3156103136607478463[308] = 0;
   out_3156103136607478463[309] = 0;
   out_3156103136607478463[310] = 0;
   out_3156103136607478463[311] = 0;
   out_3156103136607478463[312] = 0;
   out_3156103136607478463[313] = 0;
   out_3156103136607478463[314] = 0;
   out_3156103136607478463[315] = 0;
   out_3156103136607478463[316] = 0;
   out_3156103136607478463[317] = 0;
   out_3156103136607478463[318] = 0;
   out_3156103136607478463[319] = 0;
   out_3156103136607478463[320] = 0;
   out_3156103136607478463[321] = 0;
   out_3156103136607478463[322] = 0;
   out_3156103136607478463[323] = 1;
}
void h_4(double *state, double *unused, double *out_4668712772901425910) {
   out_4668712772901425910[0] = state[6] + state[9];
   out_4668712772901425910[1] = state[7] + state[10];
   out_4668712772901425910[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3277377262519307888) {
   out_3277377262519307888[0] = 0;
   out_3277377262519307888[1] = 0;
   out_3277377262519307888[2] = 0;
   out_3277377262519307888[3] = 0;
   out_3277377262519307888[4] = 0;
   out_3277377262519307888[5] = 0;
   out_3277377262519307888[6] = 1;
   out_3277377262519307888[7] = 0;
   out_3277377262519307888[8] = 0;
   out_3277377262519307888[9] = 1;
   out_3277377262519307888[10] = 0;
   out_3277377262519307888[11] = 0;
   out_3277377262519307888[12] = 0;
   out_3277377262519307888[13] = 0;
   out_3277377262519307888[14] = 0;
   out_3277377262519307888[15] = 0;
   out_3277377262519307888[16] = 0;
   out_3277377262519307888[17] = 0;
   out_3277377262519307888[18] = 0;
   out_3277377262519307888[19] = 0;
   out_3277377262519307888[20] = 0;
   out_3277377262519307888[21] = 0;
   out_3277377262519307888[22] = 0;
   out_3277377262519307888[23] = 0;
   out_3277377262519307888[24] = 0;
   out_3277377262519307888[25] = 1;
   out_3277377262519307888[26] = 0;
   out_3277377262519307888[27] = 0;
   out_3277377262519307888[28] = 1;
   out_3277377262519307888[29] = 0;
   out_3277377262519307888[30] = 0;
   out_3277377262519307888[31] = 0;
   out_3277377262519307888[32] = 0;
   out_3277377262519307888[33] = 0;
   out_3277377262519307888[34] = 0;
   out_3277377262519307888[35] = 0;
   out_3277377262519307888[36] = 0;
   out_3277377262519307888[37] = 0;
   out_3277377262519307888[38] = 0;
   out_3277377262519307888[39] = 0;
   out_3277377262519307888[40] = 0;
   out_3277377262519307888[41] = 0;
   out_3277377262519307888[42] = 0;
   out_3277377262519307888[43] = 0;
   out_3277377262519307888[44] = 1;
   out_3277377262519307888[45] = 0;
   out_3277377262519307888[46] = 0;
   out_3277377262519307888[47] = 1;
   out_3277377262519307888[48] = 0;
   out_3277377262519307888[49] = 0;
   out_3277377262519307888[50] = 0;
   out_3277377262519307888[51] = 0;
   out_3277377262519307888[52] = 0;
   out_3277377262519307888[53] = 0;
}
void h_10(double *state, double *unused, double *out_5024807863031837328) {
   out_5024807863031837328[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5024807863031837328[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5024807863031837328[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4567419581298515838) {
   out_4567419581298515838[0] = 0;
   out_4567419581298515838[1] = 9.8100000000000005*cos(state[1]);
   out_4567419581298515838[2] = 0;
   out_4567419581298515838[3] = 0;
   out_4567419581298515838[4] = -state[8];
   out_4567419581298515838[5] = state[7];
   out_4567419581298515838[6] = 0;
   out_4567419581298515838[7] = state[5];
   out_4567419581298515838[8] = -state[4];
   out_4567419581298515838[9] = 0;
   out_4567419581298515838[10] = 0;
   out_4567419581298515838[11] = 0;
   out_4567419581298515838[12] = 1;
   out_4567419581298515838[13] = 0;
   out_4567419581298515838[14] = 0;
   out_4567419581298515838[15] = 1;
   out_4567419581298515838[16] = 0;
   out_4567419581298515838[17] = 0;
   out_4567419581298515838[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4567419581298515838[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4567419581298515838[20] = 0;
   out_4567419581298515838[21] = state[8];
   out_4567419581298515838[22] = 0;
   out_4567419581298515838[23] = -state[6];
   out_4567419581298515838[24] = -state[5];
   out_4567419581298515838[25] = 0;
   out_4567419581298515838[26] = state[3];
   out_4567419581298515838[27] = 0;
   out_4567419581298515838[28] = 0;
   out_4567419581298515838[29] = 0;
   out_4567419581298515838[30] = 0;
   out_4567419581298515838[31] = 1;
   out_4567419581298515838[32] = 0;
   out_4567419581298515838[33] = 0;
   out_4567419581298515838[34] = 1;
   out_4567419581298515838[35] = 0;
   out_4567419581298515838[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4567419581298515838[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4567419581298515838[38] = 0;
   out_4567419581298515838[39] = -state[7];
   out_4567419581298515838[40] = state[6];
   out_4567419581298515838[41] = 0;
   out_4567419581298515838[42] = state[4];
   out_4567419581298515838[43] = -state[3];
   out_4567419581298515838[44] = 0;
   out_4567419581298515838[45] = 0;
   out_4567419581298515838[46] = 0;
   out_4567419581298515838[47] = 0;
   out_4567419581298515838[48] = 0;
   out_4567419581298515838[49] = 0;
   out_4567419581298515838[50] = 1;
   out_4567419581298515838[51] = 0;
   out_4567419581298515838[52] = 0;
   out_4567419581298515838[53] = 1;
}
void h_13(double *state, double *unused, double *out_711061843632216754) {
   out_711061843632216754[0] = state[3];
   out_711061843632216754[1] = state[4];
   out_711061843632216754[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4333253945797393041) {
   out_4333253945797393041[0] = 0;
   out_4333253945797393041[1] = 0;
   out_4333253945797393041[2] = 0;
   out_4333253945797393041[3] = 1;
   out_4333253945797393041[4] = 0;
   out_4333253945797393041[5] = 0;
   out_4333253945797393041[6] = 0;
   out_4333253945797393041[7] = 0;
   out_4333253945797393041[8] = 0;
   out_4333253945797393041[9] = 0;
   out_4333253945797393041[10] = 0;
   out_4333253945797393041[11] = 0;
   out_4333253945797393041[12] = 0;
   out_4333253945797393041[13] = 0;
   out_4333253945797393041[14] = 0;
   out_4333253945797393041[15] = 0;
   out_4333253945797393041[16] = 0;
   out_4333253945797393041[17] = 0;
   out_4333253945797393041[18] = 0;
   out_4333253945797393041[19] = 0;
   out_4333253945797393041[20] = 0;
   out_4333253945797393041[21] = 0;
   out_4333253945797393041[22] = 1;
   out_4333253945797393041[23] = 0;
   out_4333253945797393041[24] = 0;
   out_4333253945797393041[25] = 0;
   out_4333253945797393041[26] = 0;
   out_4333253945797393041[27] = 0;
   out_4333253945797393041[28] = 0;
   out_4333253945797393041[29] = 0;
   out_4333253945797393041[30] = 0;
   out_4333253945797393041[31] = 0;
   out_4333253945797393041[32] = 0;
   out_4333253945797393041[33] = 0;
   out_4333253945797393041[34] = 0;
   out_4333253945797393041[35] = 0;
   out_4333253945797393041[36] = 0;
   out_4333253945797393041[37] = 0;
   out_4333253945797393041[38] = 0;
   out_4333253945797393041[39] = 0;
   out_4333253945797393041[40] = 0;
   out_4333253945797393041[41] = 1;
   out_4333253945797393041[42] = 0;
   out_4333253945797393041[43] = 0;
   out_4333253945797393041[44] = 0;
   out_4333253945797393041[45] = 0;
   out_4333253945797393041[46] = 0;
   out_4333253945797393041[47] = 0;
   out_4333253945797393041[48] = 0;
   out_4333253945797393041[49] = 0;
   out_4333253945797393041[50] = 0;
   out_4333253945797393041[51] = 0;
   out_4333253945797393041[52] = 0;
   out_4333253945797393041[53] = 0;
}
void h_14(double *state, double *unused, double *out_1546878073048898636) {
   out_1546878073048898636[0] = state[6];
   out_1546878073048898636[1] = state[7];
   out_1546878073048898636[2] = state[8];
}
void H_14(double *state, double *unused, double *out_685863593820176641) {
   out_685863593820176641[0] = 0;
   out_685863593820176641[1] = 0;
   out_685863593820176641[2] = 0;
   out_685863593820176641[3] = 0;
   out_685863593820176641[4] = 0;
   out_685863593820176641[5] = 0;
   out_685863593820176641[6] = 1;
   out_685863593820176641[7] = 0;
   out_685863593820176641[8] = 0;
   out_685863593820176641[9] = 0;
   out_685863593820176641[10] = 0;
   out_685863593820176641[11] = 0;
   out_685863593820176641[12] = 0;
   out_685863593820176641[13] = 0;
   out_685863593820176641[14] = 0;
   out_685863593820176641[15] = 0;
   out_685863593820176641[16] = 0;
   out_685863593820176641[17] = 0;
   out_685863593820176641[18] = 0;
   out_685863593820176641[19] = 0;
   out_685863593820176641[20] = 0;
   out_685863593820176641[21] = 0;
   out_685863593820176641[22] = 0;
   out_685863593820176641[23] = 0;
   out_685863593820176641[24] = 0;
   out_685863593820176641[25] = 1;
   out_685863593820176641[26] = 0;
   out_685863593820176641[27] = 0;
   out_685863593820176641[28] = 0;
   out_685863593820176641[29] = 0;
   out_685863593820176641[30] = 0;
   out_685863593820176641[31] = 0;
   out_685863593820176641[32] = 0;
   out_685863593820176641[33] = 0;
   out_685863593820176641[34] = 0;
   out_685863593820176641[35] = 0;
   out_685863593820176641[36] = 0;
   out_685863593820176641[37] = 0;
   out_685863593820176641[38] = 0;
   out_685863593820176641[39] = 0;
   out_685863593820176641[40] = 0;
   out_685863593820176641[41] = 0;
   out_685863593820176641[42] = 0;
   out_685863593820176641[43] = 0;
   out_685863593820176641[44] = 1;
   out_685863593820176641[45] = 0;
   out_685863593820176641[46] = 0;
   out_685863593820176641[47] = 0;
   out_685863593820176641[48] = 0;
   out_685863593820176641[49] = 0;
   out_685863593820176641[50] = 0;
   out_685863593820176641[51] = 0;
   out_685863593820176641[52] = 0;
   out_685863593820176641[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_2903893253895971355) {
  err_fun(nom_x, delta_x, out_2903893253895971355);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3928278332152438487) {
  inv_err_fun(nom_x, true_x, out_3928278332152438487);
}
void pose_H_mod_fun(double *state, double *out_5666984403538513454) {
  H_mod_fun(state, out_5666984403538513454);
}
void pose_f_fun(double *state, double dt, double *out_3108653889513613454) {
  f_fun(state,  dt, out_3108653889513613454);
}
void pose_F_fun(double *state, double dt, double *out_3156103136607478463) {
  F_fun(state,  dt, out_3156103136607478463);
}
void pose_h_4(double *state, double *unused, double *out_4668712772901425910) {
  h_4(state, unused, out_4668712772901425910);
}
void pose_H_4(double *state, double *unused, double *out_3277377262519307888) {
  H_4(state, unused, out_3277377262519307888);
}
void pose_h_10(double *state, double *unused, double *out_5024807863031837328) {
  h_10(state, unused, out_5024807863031837328);
}
void pose_H_10(double *state, double *unused, double *out_4567419581298515838) {
  H_10(state, unused, out_4567419581298515838);
}
void pose_h_13(double *state, double *unused, double *out_711061843632216754) {
  h_13(state, unused, out_711061843632216754);
}
void pose_H_13(double *state, double *unused, double *out_4333253945797393041) {
  H_13(state, unused, out_4333253945797393041);
}
void pose_h_14(double *state, double *unused, double *out_1546878073048898636) {
  h_14(state, unused, out_1546878073048898636);
}
void pose_H_14(double *state, double *unused, double *out_685863593820176641) {
  H_14(state, unused, out_685863593820176641);
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
