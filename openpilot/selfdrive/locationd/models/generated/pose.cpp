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
void err_fun(double *nom_x, double *delta_x, double *out_7611002709956289417) {
   out_7611002709956289417[0] = delta_x[0] + nom_x[0];
   out_7611002709956289417[1] = delta_x[1] + nom_x[1];
   out_7611002709956289417[2] = delta_x[2] + nom_x[2];
   out_7611002709956289417[3] = delta_x[3] + nom_x[3];
   out_7611002709956289417[4] = delta_x[4] + nom_x[4];
   out_7611002709956289417[5] = delta_x[5] + nom_x[5];
   out_7611002709956289417[6] = delta_x[6] + nom_x[6];
   out_7611002709956289417[7] = delta_x[7] + nom_x[7];
   out_7611002709956289417[8] = delta_x[8] + nom_x[8];
   out_7611002709956289417[9] = delta_x[9] + nom_x[9];
   out_7611002709956289417[10] = delta_x[10] + nom_x[10];
   out_7611002709956289417[11] = delta_x[11] + nom_x[11];
   out_7611002709956289417[12] = delta_x[12] + nom_x[12];
   out_7611002709956289417[13] = delta_x[13] + nom_x[13];
   out_7611002709956289417[14] = delta_x[14] + nom_x[14];
   out_7611002709956289417[15] = delta_x[15] + nom_x[15];
   out_7611002709956289417[16] = delta_x[16] + nom_x[16];
   out_7611002709956289417[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2231207821854008376) {
   out_2231207821854008376[0] = -nom_x[0] + true_x[0];
   out_2231207821854008376[1] = -nom_x[1] + true_x[1];
   out_2231207821854008376[2] = -nom_x[2] + true_x[2];
   out_2231207821854008376[3] = -nom_x[3] + true_x[3];
   out_2231207821854008376[4] = -nom_x[4] + true_x[4];
   out_2231207821854008376[5] = -nom_x[5] + true_x[5];
   out_2231207821854008376[6] = -nom_x[6] + true_x[6];
   out_2231207821854008376[7] = -nom_x[7] + true_x[7];
   out_2231207821854008376[8] = -nom_x[8] + true_x[8];
   out_2231207821854008376[9] = -nom_x[9] + true_x[9];
   out_2231207821854008376[10] = -nom_x[10] + true_x[10];
   out_2231207821854008376[11] = -nom_x[11] + true_x[11];
   out_2231207821854008376[12] = -nom_x[12] + true_x[12];
   out_2231207821854008376[13] = -nom_x[13] + true_x[13];
   out_2231207821854008376[14] = -nom_x[14] + true_x[14];
   out_2231207821854008376[15] = -nom_x[15] + true_x[15];
   out_2231207821854008376[16] = -nom_x[16] + true_x[16];
   out_2231207821854008376[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6702701208743020995) {
   out_6702701208743020995[0] = 1.0;
   out_6702701208743020995[1] = 0.0;
   out_6702701208743020995[2] = 0.0;
   out_6702701208743020995[3] = 0.0;
   out_6702701208743020995[4] = 0.0;
   out_6702701208743020995[5] = 0.0;
   out_6702701208743020995[6] = 0.0;
   out_6702701208743020995[7] = 0.0;
   out_6702701208743020995[8] = 0.0;
   out_6702701208743020995[9] = 0.0;
   out_6702701208743020995[10] = 0.0;
   out_6702701208743020995[11] = 0.0;
   out_6702701208743020995[12] = 0.0;
   out_6702701208743020995[13] = 0.0;
   out_6702701208743020995[14] = 0.0;
   out_6702701208743020995[15] = 0.0;
   out_6702701208743020995[16] = 0.0;
   out_6702701208743020995[17] = 0.0;
   out_6702701208743020995[18] = 0.0;
   out_6702701208743020995[19] = 1.0;
   out_6702701208743020995[20] = 0.0;
   out_6702701208743020995[21] = 0.0;
   out_6702701208743020995[22] = 0.0;
   out_6702701208743020995[23] = 0.0;
   out_6702701208743020995[24] = 0.0;
   out_6702701208743020995[25] = 0.0;
   out_6702701208743020995[26] = 0.0;
   out_6702701208743020995[27] = 0.0;
   out_6702701208743020995[28] = 0.0;
   out_6702701208743020995[29] = 0.0;
   out_6702701208743020995[30] = 0.0;
   out_6702701208743020995[31] = 0.0;
   out_6702701208743020995[32] = 0.0;
   out_6702701208743020995[33] = 0.0;
   out_6702701208743020995[34] = 0.0;
   out_6702701208743020995[35] = 0.0;
   out_6702701208743020995[36] = 0.0;
   out_6702701208743020995[37] = 0.0;
   out_6702701208743020995[38] = 1.0;
   out_6702701208743020995[39] = 0.0;
   out_6702701208743020995[40] = 0.0;
   out_6702701208743020995[41] = 0.0;
   out_6702701208743020995[42] = 0.0;
   out_6702701208743020995[43] = 0.0;
   out_6702701208743020995[44] = 0.0;
   out_6702701208743020995[45] = 0.0;
   out_6702701208743020995[46] = 0.0;
   out_6702701208743020995[47] = 0.0;
   out_6702701208743020995[48] = 0.0;
   out_6702701208743020995[49] = 0.0;
   out_6702701208743020995[50] = 0.0;
   out_6702701208743020995[51] = 0.0;
   out_6702701208743020995[52] = 0.0;
   out_6702701208743020995[53] = 0.0;
   out_6702701208743020995[54] = 0.0;
   out_6702701208743020995[55] = 0.0;
   out_6702701208743020995[56] = 0.0;
   out_6702701208743020995[57] = 1.0;
   out_6702701208743020995[58] = 0.0;
   out_6702701208743020995[59] = 0.0;
   out_6702701208743020995[60] = 0.0;
   out_6702701208743020995[61] = 0.0;
   out_6702701208743020995[62] = 0.0;
   out_6702701208743020995[63] = 0.0;
   out_6702701208743020995[64] = 0.0;
   out_6702701208743020995[65] = 0.0;
   out_6702701208743020995[66] = 0.0;
   out_6702701208743020995[67] = 0.0;
   out_6702701208743020995[68] = 0.0;
   out_6702701208743020995[69] = 0.0;
   out_6702701208743020995[70] = 0.0;
   out_6702701208743020995[71] = 0.0;
   out_6702701208743020995[72] = 0.0;
   out_6702701208743020995[73] = 0.0;
   out_6702701208743020995[74] = 0.0;
   out_6702701208743020995[75] = 0.0;
   out_6702701208743020995[76] = 1.0;
   out_6702701208743020995[77] = 0.0;
   out_6702701208743020995[78] = 0.0;
   out_6702701208743020995[79] = 0.0;
   out_6702701208743020995[80] = 0.0;
   out_6702701208743020995[81] = 0.0;
   out_6702701208743020995[82] = 0.0;
   out_6702701208743020995[83] = 0.0;
   out_6702701208743020995[84] = 0.0;
   out_6702701208743020995[85] = 0.0;
   out_6702701208743020995[86] = 0.0;
   out_6702701208743020995[87] = 0.0;
   out_6702701208743020995[88] = 0.0;
   out_6702701208743020995[89] = 0.0;
   out_6702701208743020995[90] = 0.0;
   out_6702701208743020995[91] = 0.0;
   out_6702701208743020995[92] = 0.0;
   out_6702701208743020995[93] = 0.0;
   out_6702701208743020995[94] = 0.0;
   out_6702701208743020995[95] = 1.0;
   out_6702701208743020995[96] = 0.0;
   out_6702701208743020995[97] = 0.0;
   out_6702701208743020995[98] = 0.0;
   out_6702701208743020995[99] = 0.0;
   out_6702701208743020995[100] = 0.0;
   out_6702701208743020995[101] = 0.0;
   out_6702701208743020995[102] = 0.0;
   out_6702701208743020995[103] = 0.0;
   out_6702701208743020995[104] = 0.0;
   out_6702701208743020995[105] = 0.0;
   out_6702701208743020995[106] = 0.0;
   out_6702701208743020995[107] = 0.0;
   out_6702701208743020995[108] = 0.0;
   out_6702701208743020995[109] = 0.0;
   out_6702701208743020995[110] = 0.0;
   out_6702701208743020995[111] = 0.0;
   out_6702701208743020995[112] = 0.0;
   out_6702701208743020995[113] = 0.0;
   out_6702701208743020995[114] = 1.0;
   out_6702701208743020995[115] = 0.0;
   out_6702701208743020995[116] = 0.0;
   out_6702701208743020995[117] = 0.0;
   out_6702701208743020995[118] = 0.0;
   out_6702701208743020995[119] = 0.0;
   out_6702701208743020995[120] = 0.0;
   out_6702701208743020995[121] = 0.0;
   out_6702701208743020995[122] = 0.0;
   out_6702701208743020995[123] = 0.0;
   out_6702701208743020995[124] = 0.0;
   out_6702701208743020995[125] = 0.0;
   out_6702701208743020995[126] = 0.0;
   out_6702701208743020995[127] = 0.0;
   out_6702701208743020995[128] = 0.0;
   out_6702701208743020995[129] = 0.0;
   out_6702701208743020995[130] = 0.0;
   out_6702701208743020995[131] = 0.0;
   out_6702701208743020995[132] = 0.0;
   out_6702701208743020995[133] = 1.0;
   out_6702701208743020995[134] = 0.0;
   out_6702701208743020995[135] = 0.0;
   out_6702701208743020995[136] = 0.0;
   out_6702701208743020995[137] = 0.0;
   out_6702701208743020995[138] = 0.0;
   out_6702701208743020995[139] = 0.0;
   out_6702701208743020995[140] = 0.0;
   out_6702701208743020995[141] = 0.0;
   out_6702701208743020995[142] = 0.0;
   out_6702701208743020995[143] = 0.0;
   out_6702701208743020995[144] = 0.0;
   out_6702701208743020995[145] = 0.0;
   out_6702701208743020995[146] = 0.0;
   out_6702701208743020995[147] = 0.0;
   out_6702701208743020995[148] = 0.0;
   out_6702701208743020995[149] = 0.0;
   out_6702701208743020995[150] = 0.0;
   out_6702701208743020995[151] = 0.0;
   out_6702701208743020995[152] = 1.0;
   out_6702701208743020995[153] = 0.0;
   out_6702701208743020995[154] = 0.0;
   out_6702701208743020995[155] = 0.0;
   out_6702701208743020995[156] = 0.0;
   out_6702701208743020995[157] = 0.0;
   out_6702701208743020995[158] = 0.0;
   out_6702701208743020995[159] = 0.0;
   out_6702701208743020995[160] = 0.0;
   out_6702701208743020995[161] = 0.0;
   out_6702701208743020995[162] = 0.0;
   out_6702701208743020995[163] = 0.0;
   out_6702701208743020995[164] = 0.0;
   out_6702701208743020995[165] = 0.0;
   out_6702701208743020995[166] = 0.0;
   out_6702701208743020995[167] = 0.0;
   out_6702701208743020995[168] = 0.0;
   out_6702701208743020995[169] = 0.0;
   out_6702701208743020995[170] = 0.0;
   out_6702701208743020995[171] = 1.0;
   out_6702701208743020995[172] = 0.0;
   out_6702701208743020995[173] = 0.0;
   out_6702701208743020995[174] = 0.0;
   out_6702701208743020995[175] = 0.0;
   out_6702701208743020995[176] = 0.0;
   out_6702701208743020995[177] = 0.0;
   out_6702701208743020995[178] = 0.0;
   out_6702701208743020995[179] = 0.0;
   out_6702701208743020995[180] = 0.0;
   out_6702701208743020995[181] = 0.0;
   out_6702701208743020995[182] = 0.0;
   out_6702701208743020995[183] = 0.0;
   out_6702701208743020995[184] = 0.0;
   out_6702701208743020995[185] = 0.0;
   out_6702701208743020995[186] = 0.0;
   out_6702701208743020995[187] = 0.0;
   out_6702701208743020995[188] = 0.0;
   out_6702701208743020995[189] = 0.0;
   out_6702701208743020995[190] = 1.0;
   out_6702701208743020995[191] = 0.0;
   out_6702701208743020995[192] = 0.0;
   out_6702701208743020995[193] = 0.0;
   out_6702701208743020995[194] = 0.0;
   out_6702701208743020995[195] = 0.0;
   out_6702701208743020995[196] = 0.0;
   out_6702701208743020995[197] = 0.0;
   out_6702701208743020995[198] = 0.0;
   out_6702701208743020995[199] = 0.0;
   out_6702701208743020995[200] = 0.0;
   out_6702701208743020995[201] = 0.0;
   out_6702701208743020995[202] = 0.0;
   out_6702701208743020995[203] = 0.0;
   out_6702701208743020995[204] = 0.0;
   out_6702701208743020995[205] = 0.0;
   out_6702701208743020995[206] = 0.0;
   out_6702701208743020995[207] = 0.0;
   out_6702701208743020995[208] = 0.0;
   out_6702701208743020995[209] = 1.0;
   out_6702701208743020995[210] = 0.0;
   out_6702701208743020995[211] = 0.0;
   out_6702701208743020995[212] = 0.0;
   out_6702701208743020995[213] = 0.0;
   out_6702701208743020995[214] = 0.0;
   out_6702701208743020995[215] = 0.0;
   out_6702701208743020995[216] = 0.0;
   out_6702701208743020995[217] = 0.0;
   out_6702701208743020995[218] = 0.0;
   out_6702701208743020995[219] = 0.0;
   out_6702701208743020995[220] = 0.0;
   out_6702701208743020995[221] = 0.0;
   out_6702701208743020995[222] = 0.0;
   out_6702701208743020995[223] = 0.0;
   out_6702701208743020995[224] = 0.0;
   out_6702701208743020995[225] = 0.0;
   out_6702701208743020995[226] = 0.0;
   out_6702701208743020995[227] = 0.0;
   out_6702701208743020995[228] = 1.0;
   out_6702701208743020995[229] = 0.0;
   out_6702701208743020995[230] = 0.0;
   out_6702701208743020995[231] = 0.0;
   out_6702701208743020995[232] = 0.0;
   out_6702701208743020995[233] = 0.0;
   out_6702701208743020995[234] = 0.0;
   out_6702701208743020995[235] = 0.0;
   out_6702701208743020995[236] = 0.0;
   out_6702701208743020995[237] = 0.0;
   out_6702701208743020995[238] = 0.0;
   out_6702701208743020995[239] = 0.0;
   out_6702701208743020995[240] = 0.0;
   out_6702701208743020995[241] = 0.0;
   out_6702701208743020995[242] = 0.0;
   out_6702701208743020995[243] = 0.0;
   out_6702701208743020995[244] = 0.0;
   out_6702701208743020995[245] = 0.0;
   out_6702701208743020995[246] = 0.0;
   out_6702701208743020995[247] = 1.0;
   out_6702701208743020995[248] = 0.0;
   out_6702701208743020995[249] = 0.0;
   out_6702701208743020995[250] = 0.0;
   out_6702701208743020995[251] = 0.0;
   out_6702701208743020995[252] = 0.0;
   out_6702701208743020995[253] = 0.0;
   out_6702701208743020995[254] = 0.0;
   out_6702701208743020995[255] = 0.0;
   out_6702701208743020995[256] = 0.0;
   out_6702701208743020995[257] = 0.0;
   out_6702701208743020995[258] = 0.0;
   out_6702701208743020995[259] = 0.0;
   out_6702701208743020995[260] = 0.0;
   out_6702701208743020995[261] = 0.0;
   out_6702701208743020995[262] = 0.0;
   out_6702701208743020995[263] = 0.0;
   out_6702701208743020995[264] = 0.0;
   out_6702701208743020995[265] = 0.0;
   out_6702701208743020995[266] = 1.0;
   out_6702701208743020995[267] = 0.0;
   out_6702701208743020995[268] = 0.0;
   out_6702701208743020995[269] = 0.0;
   out_6702701208743020995[270] = 0.0;
   out_6702701208743020995[271] = 0.0;
   out_6702701208743020995[272] = 0.0;
   out_6702701208743020995[273] = 0.0;
   out_6702701208743020995[274] = 0.0;
   out_6702701208743020995[275] = 0.0;
   out_6702701208743020995[276] = 0.0;
   out_6702701208743020995[277] = 0.0;
   out_6702701208743020995[278] = 0.0;
   out_6702701208743020995[279] = 0.0;
   out_6702701208743020995[280] = 0.0;
   out_6702701208743020995[281] = 0.0;
   out_6702701208743020995[282] = 0.0;
   out_6702701208743020995[283] = 0.0;
   out_6702701208743020995[284] = 0.0;
   out_6702701208743020995[285] = 1.0;
   out_6702701208743020995[286] = 0.0;
   out_6702701208743020995[287] = 0.0;
   out_6702701208743020995[288] = 0.0;
   out_6702701208743020995[289] = 0.0;
   out_6702701208743020995[290] = 0.0;
   out_6702701208743020995[291] = 0.0;
   out_6702701208743020995[292] = 0.0;
   out_6702701208743020995[293] = 0.0;
   out_6702701208743020995[294] = 0.0;
   out_6702701208743020995[295] = 0.0;
   out_6702701208743020995[296] = 0.0;
   out_6702701208743020995[297] = 0.0;
   out_6702701208743020995[298] = 0.0;
   out_6702701208743020995[299] = 0.0;
   out_6702701208743020995[300] = 0.0;
   out_6702701208743020995[301] = 0.0;
   out_6702701208743020995[302] = 0.0;
   out_6702701208743020995[303] = 0.0;
   out_6702701208743020995[304] = 1.0;
   out_6702701208743020995[305] = 0.0;
   out_6702701208743020995[306] = 0.0;
   out_6702701208743020995[307] = 0.0;
   out_6702701208743020995[308] = 0.0;
   out_6702701208743020995[309] = 0.0;
   out_6702701208743020995[310] = 0.0;
   out_6702701208743020995[311] = 0.0;
   out_6702701208743020995[312] = 0.0;
   out_6702701208743020995[313] = 0.0;
   out_6702701208743020995[314] = 0.0;
   out_6702701208743020995[315] = 0.0;
   out_6702701208743020995[316] = 0.0;
   out_6702701208743020995[317] = 0.0;
   out_6702701208743020995[318] = 0.0;
   out_6702701208743020995[319] = 0.0;
   out_6702701208743020995[320] = 0.0;
   out_6702701208743020995[321] = 0.0;
   out_6702701208743020995[322] = 0.0;
   out_6702701208743020995[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6952086026266534103) {
   out_6952086026266534103[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6952086026266534103[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6952086026266534103[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6952086026266534103[3] = dt*state[12] + state[3];
   out_6952086026266534103[4] = dt*state[13] + state[4];
   out_6952086026266534103[5] = dt*state[14] + state[5];
   out_6952086026266534103[6] = state[6];
   out_6952086026266534103[7] = state[7];
   out_6952086026266534103[8] = state[8];
   out_6952086026266534103[9] = state[9];
   out_6952086026266534103[10] = state[10];
   out_6952086026266534103[11] = state[11];
   out_6952086026266534103[12] = state[12];
   out_6952086026266534103[13] = state[13];
   out_6952086026266534103[14] = state[14];
   out_6952086026266534103[15] = state[15];
   out_6952086026266534103[16] = state[16];
   out_6952086026266534103[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6422576820580893617) {
   out_6422576820580893617[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6422576820580893617[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6422576820580893617[2] = 0;
   out_6422576820580893617[3] = 0;
   out_6422576820580893617[4] = 0;
   out_6422576820580893617[5] = 0;
   out_6422576820580893617[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6422576820580893617[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6422576820580893617[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6422576820580893617[9] = 0;
   out_6422576820580893617[10] = 0;
   out_6422576820580893617[11] = 0;
   out_6422576820580893617[12] = 0;
   out_6422576820580893617[13] = 0;
   out_6422576820580893617[14] = 0;
   out_6422576820580893617[15] = 0;
   out_6422576820580893617[16] = 0;
   out_6422576820580893617[17] = 0;
   out_6422576820580893617[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6422576820580893617[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6422576820580893617[20] = 0;
   out_6422576820580893617[21] = 0;
   out_6422576820580893617[22] = 0;
   out_6422576820580893617[23] = 0;
   out_6422576820580893617[24] = 0;
   out_6422576820580893617[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6422576820580893617[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6422576820580893617[27] = 0;
   out_6422576820580893617[28] = 0;
   out_6422576820580893617[29] = 0;
   out_6422576820580893617[30] = 0;
   out_6422576820580893617[31] = 0;
   out_6422576820580893617[32] = 0;
   out_6422576820580893617[33] = 0;
   out_6422576820580893617[34] = 0;
   out_6422576820580893617[35] = 0;
   out_6422576820580893617[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6422576820580893617[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6422576820580893617[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6422576820580893617[39] = 0;
   out_6422576820580893617[40] = 0;
   out_6422576820580893617[41] = 0;
   out_6422576820580893617[42] = 0;
   out_6422576820580893617[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6422576820580893617[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6422576820580893617[45] = 0;
   out_6422576820580893617[46] = 0;
   out_6422576820580893617[47] = 0;
   out_6422576820580893617[48] = 0;
   out_6422576820580893617[49] = 0;
   out_6422576820580893617[50] = 0;
   out_6422576820580893617[51] = 0;
   out_6422576820580893617[52] = 0;
   out_6422576820580893617[53] = 0;
   out_6422576820580893617[54] = 0;
   out_6422576820580893617[55] = 0;
   out_6422576820580893617[56] = 0;
   out_6422576820580893617[57] = 1;
   out_6422576820580893617[58] = 0;
   out_6422576820580893617[59] = 0;
   out_6422576820580893617[60] = 0;
   out_6422576820580893617[61] = 0;
   out_6422576820580893617[62] = 0;
   out_6422576820580893617[63] = 0;
   out_6422576820580893617[64] = 0;
   out_6422576820580893617[65] = 0;
   out_6422576820580893617[66] = dt;
   out_6422576820580893617[67] = 0;
   out_6422576820580893617[68] = 0;
   out_6422576820580893617[69] = 0;
   out_6422576820580893617[70] = 0;
   out_6422576820580893617[71] = 0;
   out_6422576820580893617[72] = 0;
   out_6422576820580893617[73] = 0;
   out_6422576820580893617[74] = 0;
   out_6422576820580893617[75] = 0;
   out_6422576820580893617[76] = 1;
   out_6422576820580893617[77] = 0;
   out_6422576820580893617[78] = 0;
   out_6422576820580893617[79] = 0;
   out_6422576820580893617[80] = 0;
   out_6422576820580893617[81] = 0;
   out_6422576820580893617[82] = 0;
   out_6422576820580893617[83] = 0;
   out_6422576820580893617[84] = 0;
   out_6422576820580893617[85] = dt;
   out_6422576820580893617[86] = 0;
   out_6422576820580893617[87] = 0;
   out_6422576820580893617[88] = 0;
   out_6422576820580893617[89] = 0;
   out_6422576820580893617[90] = 0;
   out_6422576820580893617[91] = 0;
   out_6422576820580893617[92] = 0;
   out_6422576820580893617[93] = 0;
   out_6422576820580893617[94] = 0;
   out_6422576820580893617[95] = 1;
   out_6422576820580893617[96] = 0;
   out_6422576820580893617[97] = 0;
   out_6422576820580893617[98] = 0;
   out_6422576820580893617[99] = 0;
   out_6422576820580893617[100] = 0;
   out_6422576820580893617[101] = 0;
   out_6422576820580893617[102] = 0;
   out_6422576820580893617[103] = 0;
   out_6422576820580893617[104] = dt;
   out_6422576820580893617[105] = 0;
   out_6422576820580893617[106] = 0;
   out_6422576820580893617[107] = 0;
   out_6422576820580893617[108] = 0;
   out_6422576820580893617[109] = 0;
   out_6422576820580893617[110] = 0;
   out_6422576820580893617[111] = 0;
   out_6422576820580893617[112] = 0;
   out_6422576820580893617[113] = 0;
   out_6422576820580893617[114] = 1;
   out_6422576820580893617[115] = 0;
   out_6422576820580893617[116] = 0;
   out_6422576820580893617[117] = 0;
   out_6422576820580893617[118] = 0;
   out_6422576820580893617[119] = 0;
   out_6422576820580893617[120] = 0;
   out_6422576820580893617[121] = 0;
   out_6422576820580893617[122] = 0;
   out_6422576820580893617[123] = 0;
   out_6422576820580893617[124] = 0;
   out_6422576820580893617[125] = 0;
   out_6422576820580893617[126] = 0;
   out_6422576820580893617[127] = 0;
   out_6422576820580893617[128] = 0;
   out_6422576820580893617[129] = 0;
   out_6422576820580893617[130] = 0;
   out_6422576820580893617[131] = 0;
   out_6422576820580893617[132] = 0;
   out_6422576820580893617[133] = 1;
   out_6422576820580893617[134] = 0;
   out_6422576820580893617[135] = 0;
   out_6422576820580893617[136] = 0;
   out_6422576820580893617[137] = 0;
   out_6422576820580893617[138] = 0;
   out_6422576820580893617[139] = 0;
   out_6422576820580893617[140] = 0;
   out_6422576820580893617[141] = 0;
   out_6422576820580893617[142] = 0;
   out_6422576820580893617[143] = 0;
   out_6422576820580893617[144] = 0;
   out_6422576820580893617[145] = 0;
   out_6422576820580893617[146] = 0;
   out_6422576820580893617[147] = 0;
   out_6422576820580893617[148] = 0;
   out_6422576820580893617[149] = 0;
   out_6422576820580893617[150] = 0;
   out_6422576820580893617[151] = 0;
   out_6422576820580893617[152] = 1;
   out_6422576820580893617[153] = 0;
   out_6422576820580893617[154] = 0;
   out_6422576820580893617[155] = 0;
   out_6422576820580893617[156] = 0;
   out_6422576820580893617[157] = 0;
   out_6422576820580893617[158] = 0;
   out_6422576820580893617[159] = 0;
   out_6422576820580893617[160] = 0;
   out_6422576820580893617[161] = 0;
   out_6422576820580893617[162] = 0;
   out_6422576820580893617[163] = 0;
   out_6422576820580893617[164] = 0;
   out_6422576820580893617[165] = 0;
   out_6422576820580893617[166] = 0;
   out_6422576820580893617[167] = 0;
   out_6422576820580893617[168] = 0;
   out_6422576820580893617[169] = 0;
   out_6422576820580893617[170] = 0;
   out_6422576820580893617[171] = 1;
   out_6422576820580893617[172] = 0;
   out_6422576820580893617[173] = 0;
   out_6422576820580893617[174] = 0;
   out_6422576820580893617[175] = 0;
   out_6422576820580893617[176] = 0;
   out_6422576820580893617[177] = 0;
   out_6422576820580893617[178] = 0;
   out_6422576820580893617[179] = 0;
   out_6422576820580893617[180] = 0;
   out_6422576820580893617[181] = 0;
   out_6422576820580893617[182] = 0;
   out_6422576820580893617[183] = 0;
   out_6422576820580893617[184] = 0;
   out_6422576820580893617[185] = 0;
   out_6422576820580893617[186] = 0;
   out_6422576820580893617[187] = 0;
   out_6422576820580893617[188] = 0;
   out_6422576820580893617[189] = 0;
   out_6422576820580893617[190] = 1;
   out_6422576820580893617[191] = 0;
   out_6422576820580893617[192] = 0;
   out_6422576820580893617[193] = 0;
   out_6422576820580893617[194] = 0;
   out_6422576820580893617[195] = 0;
   out_6422576820580893617[196] = 0;
   out_6422576820580893617[197] = 0;
   out_6422576820580893617[198] = 0;
   out_6422576820580893617[199] = 0;
   out_6422576820580893617[200] = 0;
   out_6422576820580893617[201] = 0;
   out_6422576820580893617[202] = 0;
   out_6422576820580893617[203] = 0;
   out_6422576820580893617[204] = 0;
   out_6422576820580893617[205] = 0;
   out_6422576820580893617[206] = 0;
   out_6422576820580893617[207] = 0;
   out_6422576820580893617[208] = 0;
   out_6422576820580893617[209] = 1;
   out_6422576820580893617[210] = 0;
   out_6422576820580893617[211] = 0;
   out_6422576820580893617[212] = 0;
   out_6422576820580893617[213] = 0;
   out_6422576820580893617[214] = 0;
   out_6422576820580893617[215] = 0;
   out_6422576820580893617[216] = 0;
   out_6422576820580893617[217] = 0;
   out_6422576820580893617[218] = 0;
   out_6422576820580893617[219] = 0;
   out_6422576820580893617[220] = 0;
   out_6422576820580893617[221] = 0;
   out_6422576820580893617[222] = 0;
   out_6422576820580893617[223] = 0;
   out_6422576820580893617[224] = 0;
   out_6422576820580893617[225] = 0;
   out_6422576820580893617[226] = 0;
   out_6422576820580893617[227] = 0;
   out_6422576820580893617[228] = 1;
   out_6422576820580893617[229] = 0;
   out_6422576820580893617[230] = 0;
   out_6422576820580893617[231] = 0;
   out_6422576820580893617[232] = 0;
   out_6422576820580893617[233] = 0;
   out_6422576820580893617[234] = 0;
   out_6422576820580893617[235] = 0;
   out_6422576820580893617[236] = 0;
   out_6422576820580893617[237] = 0;
   out_6422576820580893617[238] = 0;
   out_6422576820580893617[239] = 0;
   out_6422576820580893617[240] = 0;
   out_6422576820580893617[241] = 0;
   out_6422576820580893617[242] = 0;
   out_6422576820580893617[243] = 0;
   out_6422576820580893617[244] = 0;
   out_6422576820580893617[245] = 0;
   out_6422576820580893617[246] = 0;
   out_6422576820580893617[247] = 1;
   out_6422576820580893617[248] = 0;
   out_6422576820580893617[249] = 0;
   out_6422576820580893617[250] = 0;
   out_6422576820580893617[251] = 0;
   out_6422576820580893617[252] = 0;
   out_6422576820580893617[253] = 0;
   out_6422576820580893617[254] = 0;
   out_6422576820580893617[255] = 0;
   out_6422576820580893617[256] = 0;
   out_6422576820580893617[257] = 0;
   out_6422576820580893617[258] = 0;
   out_6422576820580893617[259] = 0;
   out_6422576820580893617[260] = 0;
   out_6422576820580893617[261] = 0;
   out_6422576820580893617[262] = 0;
   out_6422576820580893617[263] = 0;
   out_6422576820580893617[264] = 0;
   out_6422576820580893617[265] = 0;
   out_6422576820580893617[266] = 1;
   out_6422576820580893617[267] = 0;
   out_6422576820580893617[268] = 0;
   out_6422576820580893617[269] = 0;
   out_6422576820580893617[270] = 0;
   out_6422576820580893617[271] = 0;
   out_6422576820580893617[272] = 0;
   out_6422576820580893617[273] = 0;
   out_6422576820580893617[274] = 0;
   out_6422576820580893617[275] = 0;
   out_6422576820580893617[276] = 0;
   out_6422576820580893617[277] = 0;
   out_6422576820580893617[278] = 0;
   out_6422576820580893617[279] = 0;
   out_6422576820580893617[280] = 0;
   out_6422576820580893617[281] = 0;
   out_6422576820580893617[282] = 0;
   out_6422576820580893617[283] = 0;
   out_6422576820580893617[284] = 0;
   out_6422576820580893617[285] = 1;
   out_6422576820580893617[286] = 0;
   out_6422576820580893617[287] = 0;
   out_6422576820580893617[288] = 0;
   out_6422576820580893617[289] = 0;
   out_6422576820580893617[290] = 0;
   out_6422576820580893617[291] = 0;
   out_6422576820580893617[292] = 0;
   out_6422576820580893617[293] = 0;
   out_6422576820580893617[294] = 0;
   out_6422576820580893617[295] = 0;
   out_6422576820580893617[296] = 0;
   out_6422576820580893617[297] = 0;
   out_6422576820580893617[298] = 0;
   out_6422576820580893617[299] = 0;
   out_6422576820580893617[300] = 0;
   out_6422576820580893617[301] = 0;
   out_6422576820580893617[302] = 0;
   out_6422576820580893617[303] = 0;
   out_6422576820580893617[304] = 1;
   out_6422576820580893617[305] = 0;
   out_6422576820580893617[306] = 0;
   out_6422576820580893617[307] = 0;
   out_6422576820580893617[308] = 0;
   out_6422576820580893617[309] = 0;
   out_6422576820580893617[310] = 0;
   out_6422576820580893617[311] = 0;
   out_6422576820580893617[312] = 0;
   out_6422576820580893617[313] = 0;
   out_6422576820580893617[314] = 0;
   out_6422576820580893617[315] = 0;
   out_6422576820580893617[316] = 0;
   out_6422576820580893617[317] = 0;
   out_6422576820580893617[318] = 0;
   out_6422576820580893617[319] = 0;
   out_6422576820580893617[320] = 0;
   out_6422576820580893617[321] = 0;
   out_6422576820580893617[322] = 0;
   out_6422576820580893617[323] = 1;
}
void h_4(double *state, double *unused, double *out_2343258124227340986) {
   out_2343258124227340986[0] = state[6] + state[9];
   out_2343258124227340986[1] = state[7] + state[10];
   out_2343258124227340986[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_2731058445052846129) {
   out_2731058445052846129[0] = 0;
   out_2731058445052846129[1] = 0;
   out_2731058445052846129[2] = 0;
   out_2731058445052846129[3] = 0;
   out_2731058445052846129[4] = 0;
   out_2731058445052846129[5] = 0;
   out_2731058445052846129[6] = 1;
   out_2731058445052846129[7] = 0;
   out_2731058445052846129[8] = 0;
   out_2731058445052846129[9] = 1;
   out_2731058445052846129[10] = 0;
   out_2731058445052846129[11] = 0;
   out_2731058445052846129[12] = 0;
   out_2731058445052846129[13] = 0;
   out_2731058445052846129[14] = 0;
   out_2731058445052846129[15] = 0;
   out_2731058445052846129[16] = 0;
   out_2731058445052846129[17] = 0;
   out_2731058445052846129[18] = 0;
   out_2731058445052846129[19] = 0;
   out_2731058445052846129[20] = 0;
   out_2731058445052846129[21] = 0;
   out_2731058445052846129[22] = 0;
   out_2731058445052846129[23] = 0;
   out_2731058445052846129[24] = 0;
   out_2731058445052846129[25] = 1;
   out_2731058445052846129[26] = 0;
   out_2731058445052846129[27] = 0;
   out_2731058445052846129[28] = 1;
   out_2731058445052846129[29] = 0;
   out_2731058445052846129[30] = 0;
   out_2731058445052846129[31] = 0;
   out_2731058445052846129[32] = 0;
   out_2731058445052846129[33] = 0;
   out_2731058445052846129[34] = 0;
   out_2731058445052846129[35] = 0;
   out_2731058445052846129[36] = 0;
   out_2731058445052846129[37] = 0;
   out_2731058445052846129[38] = 0;
   out_2731058445052846129[39] = 0;
   out_2731058445052846129[40] = 0;
   out_2731058445052846129[41] = 0;
   out_2731058445052846129[42] = 0;
   out_2731058445052846129[43] = 0;
   out_2731058445052846129[44] = 1;
   out_2731058445052846129[45] = 0;
   out_2731058445052846129[46] = 0;
   out_2731058445052846129[47] = 1;
   out_2731058445052846129[48] = 0;
   out_2731058445052846129[49] = 0;
   out_2731058445052846129[50] = 0;
   out_2731058445052846129[51] = 0;
   out_2731058445052846129[52] = 0;
   out_2731058445052846129[53] = 0;
}
void h_10(double *state, double *unused, double *out_2458659875279043295) {
   out_2458659875279043295[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2458659875279043295[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2458659875279043295[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_605941240178618613) {
   out_605941240178618613[0] = 0;
   out_605941240178618613[1] = 9.8100000000000005*cos(state[1]);
   out_605941240178618613[2] = 0;
   out_605941240178618613[3] = 0;
   out_605941240178618613[4] = -state[8];
   out_605941240178618613[5] = state[7];
   out_605941240178618613[6] = 0;
   out_605941240178618613[7] = state[5];
   out_605941240178618613[8] = -state[4];
   out_605941240178618613[9] = 0;
   out_605941240178618613[10] = 0;
   out_605941240178618613[11] = 0;
   out_605941240178618613[12] = 1;
   out_605941240178618613[13] = 0;
   out_605941240178618613[14] = 0;
   out_605941240178618613[15] = 1;
   out_605941240178618613[16] = 0;
   out_605941240178618613[17] = 0;
   out_605941240178618613[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_605941240178618613[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_605941240178618613[20] = 0;
   out_605941240178618613[21] = state[8];
   out_605941240178618613[22] = 0;
   out_605941240178618613[23] = -state[6];
   out_605941240178618613[24] = -state[5];
   out_605941240178618613[25] = 0;
   out_605941240178618613[26] = state[3];
   out_605941240178618613[27] = 0;
   out_605941240178618613[28] = 0;
   out_605941240178618613[29] = 0;
   out_605941240178618613[30] = 0;
   out_605941240178618613[31] = 1;
   out_605941240178618613[32] = 0;
   out_605941240178618613[33] = 0;
   out_605941240178618613[34] = 1;
   out_605941240178618613[35] = 0;
   out_605941240178618613[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_605941240178618613[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_605941240178618613[38] = 0;
   out_605941240178618613[39] = -state[7];
   out_605941240178618613[40] = state[6];
   out_605941240178618613[41] = 0;
   out_605941240178618613[42] = state[4];
   out_605941240178618613[43] = -state[3];
   out_605941240178618613[44] = 0;
   out_605941240178618613[45] = 0;
   out_605941240178618613[46] = 0;
   out_605941240178618613[47] = 0;
   out_605941240178618613[48] = 0;
   out_605941240178618613[49] = 0;
   out_605941240178618613[50] = 1;
   out_605941240178618613[51] = 0;
   out_605941240178618613[52] = 0;
   out_605941240178618613[53] = 1;
}
void h_13(double *state, double *unused, double *out_819965896496064494) {
   out_819965896496064494[0] = state[3];
   out_819965896496064494[1] = state[4];
   out_819965896496064494[2] = state[5];
}
void H_13(double *state, double *unused, double *out_481215380279486672) {
   out_481215380279486672[0] = 0;
   out_481215380279486672[1] = 0;
   out_481215380279486672[2] = 0;
   out_481215380279486672[3] = 1;
   out_481215380279486672[4] = 0;
   out_481215380279486672[5] = 0;
   out_481215380279486672[6] = 0;
   out_481215380279486672[7] = 0;
   out_481215380279486672[8] = 0;
   out_481215380279486672[9] = 0;
   out_481215380279486672[10] = 0;
   out_481215380279486672[11] = 0;
   out_481215380279486672[12] = 0;
   out_481215380279486672[13] = 0;
   out_481215380279486672[14] = 0;
   out_481215380279486672[15] = 0;
   out_481215380279486672[16] = 0;
   out_481215380279486672[17] = 0;
   out_481215380279486672[18] = 0;
   out_481215380279486672[19] = 0;
   out_481215380279486672[20] = 0;
   out_481215380279486672[21] = 0;
   out_481215380279486672[22] = 1;
   out_481215380279486672[23] = 0;
   out_481215380279486672[24] = 0;
   out_481215380279486672[25] = 0;
   out_481215380279486672[26] = 0;
   out_481215380279486672[27] = 0;
   out_481215380279486672[28] = 0;
   out_481215380279486672[29] = 0;
   out_481215380279486672[30] = 0;
   out_481215380279486672[31] = 0;
   out_481215380279486672[32] = 0;
   out_481215380279486672[33] = 0;
   out_481215380279486672[34] = 0;
   out_481215380279486672[35] = 0;
   out_481215380279486672[36] = 0;
   out_481215380279486672[37] = 0;
   out_481215380279486672[38] = 0;
   out_481215380279486672[39] = 0;
   out_481215380279486672[40] = 0;
   out_481215380279486672[41] = 1;
   out_481215380279486672[42] = 0;
   out_481215380279486672[43] = 0;
   out_481215380279486672[44] = 0;
   out_481215380279486672[45] = 0;
   out_481215380279486672[46] = 0;
   out_481215380279486672[47] = 0;
   out_481215380279486672[48] = 0;
   out_481215380279486672[49] = 0;
   out_481215380279486672[50] = 0;
   out_481215380279486672[51] = 0;
   out_481215380279486672[52] = 0;
   out_481215380279486672[53] = 0;
}
void h_14(double *state, double *unused, double *out_4282191208550667364) {
   out_4282191208550667364[0] = state[6];
   out_4282191208550667364[1] = state[7];
   out_4282191208550667364[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1232182411286638400) {
   out_1232182411286638400[0] = 0;
   out_1232182411286638400[1] = 0;
   out_1232182411286638400[2] = 0;
   out_1232182411286638400[3] = 0;
   out_1232182411286638400[4] = 0;
   out_1232182411286638400[5] = 0;
   out_1232182411286638400[6] = 1;
   out_1232182411286638400[7] = 0;
   out_1232182411286638400[8] = 0;
   out_1232182411286638400[9] = 0;
   out_1232182411286638400[10] = 0;
   out_1232182411286638400[11] = 0;
   out_1232182411286638400[12] = 0;
   out_1232182411286638400[13] = 0;
   out_1232182411286638400[14] = 0;
   out_1232182411286638400[15] = 0;
   out_1232182411286638400[16] = 0;
   out_1232182411286638400[17] = 0;
   out_1232182411286638400[18] = 0;
   out_1232182411286638400[19] = 0;
   out_1232182411286638400[20] = 0;
   out_1232182411286638400[21] = 0;
   out_1232182411286638400[22] = 0;
   out_1232182411286638400[23] = 0;
   out_1232182411286638400[24] = 0;
   out_1232182411286638400[25] = 1;
   out_1232182411286638400[26] = 0;
   out_1232182411286638400[27] = 0;
   out_1232182411286638400[28] = 0;
   out_1232182411286638400[29] = 0;
   out_1232182411286638400[30] = 0;
   out_1232182411286638400[31] = 0;
   out_1232182411286638400[32] = 0;
   out_1232182411286638400[33] = 0;
   out_1232182411286638400[34] = 0;
   out_1232182411286638400[35] = 0;
   out_1232182411286638400[36] = 0;
   out_1232182411286638400[37] = 0;
   out_1232182411286638400[38] = 0;
   out_1232182411286638400[39] = 0;
   out_1232182411286638400[40] = 0;
   out_1232182411286638400[41] = 0;
   out_1232182411286638400[42] = 0;
   out_1232182411286638400[43] = 0;
   out_1232182411286638400[44] = 1;
   out_1232182411286638400[45] = 0;
   out_1232182411286638400[46] = 0;
   out_1232182411286638400[47] = 0;
   out_1232182411286638400[48] = 0;
   out_1232182411286638400[49] = 0;
   out_1232182411286638400[50] = 0;
   out_1232182411286638400[51] = 0;
   out_1232182411286638400[52] = 0;
   out_1232182411286638400[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7611002709956289417) {
  err_fun(nom_x, delta_x, out_7611002709956289417);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2231207821854008376) {
  inv_err_fun(nom_x, true_x, out_2231207821854008376);
}
void pose_H_mod_fun(double *state, double *out_6702701208743020995) {
  H_mod_fun(state, out_6702701208743020995);
}
void pose_f_fun(double *state, double dt, double *out_6952086026266534103) {
  f_fun(state,  dt, out_6952086026266534103);
}
void pose_F_fun(double *state, double dt, double *out_6422576820580893617) {
  F_fun(state,  dt, out_6422576820580893617);
}
void pose_h_4(double *state, double *unused, double *out_2343258124227340986) {
  h_4(state, unused, out_2343258124227340986);
}
void pose_H_4(double *state, double *unused, double *out_2731058445052846129) {
  H_4(state, unused, out_2731058445052846129);
}
void pose_h_10(double *state, double *unused, double *out_2458659875279043295) {
  h_10(state, unused, out_2458659875279043295);
}
void pose_H_10(double *state, double *unused, double *out_605941240178618613) {
  H_10(state, unused, out_605941240178618613);
}
void pose_h_13(double *state, double *unused, double *out_819965896496064494) {
  h_13(state, unused, out_819965896496064494);
}
void pose_H_13(double *state, double *unused, double *out_481215380279486672) {
  H_13(state, unused, out_481215380279486672);
}
void pose_h_14(double *state, double *unused, double *out_4282191208550667364) {
  h_14(state, unused, out_4282191208550667364);
}
void pose_H_14(double *state, double *unused, double *out_1232182411286638400) {
  H_14(state, unused, out_1232182411286638400);
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
