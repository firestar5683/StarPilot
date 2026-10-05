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
void err_fun(double *nom_x, double *delta_x, double *out_1774761985787739244) {
   out_1774761985787739244[0] = delta_x[0] + nom_x[0];
   out_1774761985787739244[1] = delta_x[1] + nom_x[1];
   out_1774761985787739244[2] = delta_x[2] + nom_x[2];
   out_1774761985787739244[3] = delta_x[3] + nom_x[3];
   out_1774761985787739244[4] = delta_x[4] + nom_x[4];
   out_1774761985787739244[5] = delta_x[5] + nom_x[5];
   out_1774761985787739244[6] = delta_x[6] + nom_x[6];
   out_1774761985787739244[7] = delta_x[7] + nom_x[7];
   out_1774761985787739244[8] = delta_x[8] + nom_x[8];
   out_1774761985787739244[9] = delta_x[9] + nom_x[9];
   out_1774761985787739244[10] = delta_x[10] + nom_x[10];
   out_1774761985787739244[11] = delta_x[11] + nom_x[11];
   out_1774761985787739244[12] = delta_x[12] + nom_x[12];
   out_1774761985787739244[13] = delta_x[13] + nom_x[13];
   out_1774761985787739244[14] = delta_x[14] + nom_x[14];
   out_1774761985787739244[15] = delta_x[15] + nom_x[15];
   out_1774761985787739244[16] = delta_x[16] + nom_x[16];
   out_1774761985787739244[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1588823582514134997) {
   out_1588823582514134997[0] = -nom_x[0] + true_x[0];
   out_1588823582514134997[1] = -nom_x[1] + true_x[1];
   out_1588823582514134997[2] = -nom_x[2] + true_x[2];
   out_1588823582514134997[3] = -nom_x[3] + true_x[3];
   out_1588823582514134997[4] = -nom_x[4] + true_x[4];
   out_1588823582514134997[5] = -nom_x[5] + true_x[5];
   out_1588823582514134997[6] = -nom_x[6] + true_x[6];
   out_1588823582514134997[7] = -nom_x[7] + true_x[7];
   out_1588823582514134997[8] = -nom_x[8] + true_x[8];
   out_1588823582514134997[9] = -nom_x[9] + true_x[9];
   out_1588823582514134997[10] = -nom_x[10] + true_x[10];
   out_1588823582514134997[11] = -nom_x[11] + true_x[11];
   out_1588823582514134997[12] = -nom_x[12] + true_x[12];
   out_1588823582514134997[13] = -nom_x[13] + true_x[13];
   out_1588823582514134997[14] = -nom_x[14] + true_x[14];
   out_1588823582514134997[15] = -nom_x[15] + true_x[15];
   out_1588823582514134997[16] = -nom_x[16] + true_x[16];
   out_1588823582514134997[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6762725012352014604) {
   out_6762725012352014604[0] = 1.0;
   out_6762725012352014604[1] = 0.0;
   out_6762725012352014604[2] = 0.0;
   out_6762725012352014604[3] = 0.0;
   out_6762725012352014604[4] = 0.0;
   out_6762725012352014604[5] = 0.0;
   out_6762725012352014604[6] = 0.0;
   out_6762725012352014604[7] = 0.0;
   out_6762725012352014604[8] = 0.0;
   out_6762725012352014604[9] = 0.0;
   out_6762725012352014604[10] = 0.0;
   out_6762725012352014604[11] = 0.0;
   out_6762725012352014604[12] = 0.0;
   out_6762725012352014604[13] = 0.0;
   out_6762725012352014604[14] = 0.0;
   out_6762725012352014604[15] = 0.0;
   out_6762725012352014604[16] = 0.0;
   out_6762725012352014604[17] = 0.0;
   out_6762725012352014604[18] = 0.0;
   out_6762725012352014604[19] = 1.0;
   out_6762725012352014604[20] = 0.0;
   out_6762725012352014604[21] = 0.0;
   out_6762725012352014604[22] = 0.0;
   out_6762725012352014604[23] = 0.0;
   out_6762725012352014604[24] = 0.0;
   out_6762725012352014604[25] = 0.0;
   out_6762725012352014604[26] = 0.0;
   out_6762725012352014604[27] = 0.0;
   out_6762725012352014604[28] = 0.0;
   out_6762725012352014604[29] = 0.0;
   out_6762725012352014604[30] = 0.0;
   out_6762725012352014604[31] = 0.0;
   out_6762725012352014604[32] = 0.0;
   out_6762725012352014604[33] = 0.0;
   out_6762725012352014604[34] = 0.0;
   out_6762725012352014604[35] = 0.0;
   out_6762725012352014604[36] = 0.0;
   out_6762725012352014604[37] = 0.0;
   out_6762725012352014604[38] = 1.0;
   out_6762725012352014604[39] = 0.0;
   out_6762725012352014604[40] = 0.0;
   out_6762725012352014604[41] = 0.0;
   out_6762725012352014604[42] = 0.0;
   out_6762725012352014604[43] = 0.0;
   out_6762725012352014604[44] = 0.0;
   out_6762725012352014604[45] = 0.0;
   out_6762725012352014604[46] = 0.0;
   out_6762725012352014604[47] = 0.0;
   out_6762725012352014604[48] = 0.0;
   out_6762725012352014604[49] = 0.0;
   out_6762725012352014604[50] = 0.0;
   out_6762725012352014604[51] = 0.0;
   out_6762725012352014604[52] = 0.0;
   out_6762725012352014604[53] = 0.0;
   out_6762725012352014604[54] = 0.0;
   out_6762725012352014604[55] = 0.0;
   out_6762725012352014604[56] = 0.0;
   out_6762725012352014604[57] = 1.0;
   out_6762725012352014604[58] = 0.0;
   out_6762725012352014604[59] = 0.0;
   out_6762725012352014604[60] = 0.0;
   out_6762725012352014604[61] = 0.0;
   out_6762725012352014604[62] = 0.0;
   out_6762725012352014604[63] = 0.0;
   out_6762725012352014604[64] = 0.0;
   out_6762725012352014604[65] = 0.0;
   out_6762725012352014604[66] = 0.0;
   out_6762725012352014604[67] = 0.0;
   out_6762725012352014604[68] = 0.0;
   out_6762725012352014604[69] = 0.0;
   out_6762725012352014604[70] = 0.0;
   out_6762725012352014604[71] = 0.0;
   out_6762725012352014604[72] = 0.0;
   out_6762725012352014604[73] = 0.0;
   out_6762725012352014604[74] = 0.0;
   out_6762725012352014604[75] = 0.0;
   out_6762725012352014604[76] = 1.0;
   out_6762725012352014604[77] = 0.0;
   out_6762725012352014604[78] = 0.0;
   out_6762725012352014604[79] = 0.0;
   out_6762725012352014604[80] = 0.0;
   out_6762725012352014604[81] = 0.0;
   out_6762725012352014604[82] = 0.0;
   out_6762725012352014604[83] = 0.0;
   out_6762725012352014604[84] = 0.0;
   out_6762725012352014604[85] = 0.0;
   out_6762725012352014604[86] = 0.0;
   out_6762725012352014604[87] = 0.0;
   out_6762725012352014604[88] = 0.0;
   out_6762725012352014604[89] = 0.0;
   out_6762725012352014604[90] = 0.0;
   out_6762725012352014604[91] = 0.0;
   out_6762725012352014604[92] = 0.0;
   out_6762725012352014604[93] = 0.0;
   out_6762725012352014604[94] = 0.0;
   out_6762725012352014604[95] = 1.0;
   out_6762725012352014604[96] = 0.0;
   out_6762725012352014604[97] = 0.0;
   out_6762725012352014604[98] = 0.0;
   out_6762725012352014604[99] = 0.0;
   out_6762725012352014604[100] = 0.0;
   out_6762725012352014604[101] = 0.0;
   out_6762725012352014604[102] = 0.0;
   out_6762725012352014604[103] = 0.0;
   out_6762725012352014604[104] = 0.0;
   out_6762725012352014604[105] = 0.0;
   out_6762725012352014604[106] = 0.0;
   out_6762725012352014604[107] = 0.0;
   out_6762725012352014604[108] = 0.0;
   out_6762725012352014604[109] = 0.0;
   out_6762725012352014604[110] = 0.0;
   out_6762725012352014604[111] = 0.0;
   out_6762725012352014604[112] = 0.0;
   out_6762725012352014604[113] = 0.0;
   out_6762725012352014604[114] = 1.0;
   out_6762725012352014604[115] = 0.0;
   out_6762725012352014604[116] = 0.0;
   out_6762725012352014604[117] = 0.0;
   out_6762725012352014604[118] = 0.0;
   out_6762725012352014604[119] = 0.0;
   out_6762725012352014604[120] = 0.0;
   out_6762725012352014604[121] = 0.0;
   out_6762725012352014604[122] = 0.0;
   out_6762725012352014604[123] = 0.0;
   out_6762725012352014604[124] = 0.0;
   out_6762725012352014604[125] = 0.0;
   out_6762725012352014604[126] = 0.0;
   out_6762725012352014604[127] = 0.0;
   out_6762725012352014604[128] = 0.0;
   out_6762725012352014604[129] = 0.0;
   out_6762725012352014604[130] = 0.0;
   out_6762725012352014604[131] = 0.0;
   out_6762725012352014604[132] = 0.0;
   out_6762725012352014604[133] = 1.0;
   out_6762725012352014604[134] = 0.0;
   out_6762725012352014604[135] = 0.0;
   out_6762725012352014604[136] = 0.0;
   out_6762725012352014604[137] = 0.0;
   out_6762725012352014604[138] = 0.0;
   out_6762725012352014604[139] = 0.0;
   out_6762725012352014604[140] = 0.0;
   out_6762725012352014604[141] = 0.0;
   out_6762725012352014604[142] = 0.0;
   out_6762725012352014604[143] = 0.0;
   out_6762725012352014604[144] = 0.0;
   out_6762725012352014604[145] = 0.0;
   out_6762725012352014604[146] = 0.0;
   out_6762725012352014604[147] = 0.0;
   out_6762725012352014604[148] = 0.0;
   out_6762725012352014604[149] = 0.0;
   out_6762725012352014604[150] = 0.0;
   out_6762725012352014604[151] = 0.0;
   out_6762725012352014604[152] = 1.0;
   out_6762725012352014604[153] = 0.0;
   out_6762725012352014604[154] = 0.0;
   out_6762725012352014604[155] = 0.0;
   out_6762725012352014604[156] = 0.0;
   out_6762725012352014604[157] = 0.0;
   out_6762725012352014604[158] = 0.0;
   out_6762725012352014604[159] = 0.0;
   out_6762725012352014604[160] = 0.0;
   out_6762725012352014604[161] = 0.0;
   out_6762725012352014604[162] = 0.0;
   out_6762725012352014604[163] = 0.0;
   out_6762725012352014604[164] = 0.0;
   out_6762725012352014604[165] = 0.0;
   out_6762725012352014604[166] = 0.0;
   out_6762725012352014604[167] = 0.0;
   out_6762725012352014604[168] = 0.0;
   out_6762725012352014604[169] = 0.0;
   out_6762725012352014604[170] = 0.0;
   out_6762725012352014604[171] = 1.0;
   out_6762725012352014604[172] = 0.0;
   out_6762725012352014604[173] = 0.0;
   out_6762725012352014604[174] = 0.0;
   out_6762725012352014604[175] = 0.0;
   out_6762725012352014604[176] = 0.0;
   out_6762725012352014604[177] = 0.0;
   out_6762725012352014604[178] = 0.0;
   out_6762725012352014604[179] = 0.0;
   out_6762725012352014604[180] = 0.0;
   out_6762725012352014604[181] = 0.0;
   out_6762725012352014604[182] = 0.0;
   out_6762725012352014604[183] = 0.0;
   out_6762725012352014604[184] = 0.0;
   out_6762725012352014604[185] = 0.0;
   out_6762725012352014604[186] = 0.0;
   out_6762725012352014604[187] = 0.0;
   out_6762725012352014604[188] = 0.0;
   out_6762725012352014604[189] = 0.0;
   out_6762725012352014604[190] = 1.0;
   out_6762725012352014604[191] = 0.0;
   out_6762725012352014604[192] = 0.0;
   out_6762725012352014604[193] = 0.0;
   out_6762725012352014604[194] = 0.0;
   out_6762725012352014604[195] = 0.0;
   out_6762725012352014604[196] = 0.0;
   out_6762725012352014604[197] = 0.0;
   out_6762725012352014604[198] = 0.0;
   out_6762725012352014604[199] = 0.0;
   out_6762725012352014604[200] = 0.0;
   out_6762725012352014604[201] = 0.0;
   out_6762725012352014604[202] = 0.0;
   out_6762725012352014604[203] = 0.0;
   out_6762725012352014604[204] = 0.0;
   out_6762725012352014604[205] = 0.0;
   out_6762725012352014604[206] = 0.0;
   out_6762725012352014604[207] = 0.0;
   out_6762725012352014604[208] = 0.0;
   out_6762725012352014604[209] = 1.0;
   out_6762725012352014604[210] = 0.0;
   out_6762725012352014604[211] = 0.0;
   out_6762725012352014604[212] = 0.0;
   out_6762725012352014604[213] = 0.0;
   out_6762725012352014604[214] = 0.0;
   out_6762725012352014604[215] = 0.0;
   out_6762725012352014604[216] = 0.0;
   out_6762725012352014604[217] = 0.0;
   out_6762725012352014604[218] = 0.0;
   out_6762725012352014604[219] = 0.0;
   out_6762725012352014604[220] = 0.0;
   out_6762725012352014604[221] = 0.0;
   out_6762725012352014604[222] = 0.0;
   out_6762725012352014604[223] = 0.0;
   out_6762725012352014604[224] = 0.0;
   out_6762725012352014604[225] = 0.0;
   out_6762725012352014604[226] = 0.0;
   out_6762725012352014604[227] = 0.0;
   out_6762725012352014604[228] = 1.0;
   out_6762725012352014604[229] = 0.0;
   out_6762725012352014604[230] = 0.0;
   out_6762725012352014604[231] = 0.0;
   out_6762725012352014604[232] = 0.0;
   out_6762725012352014604[233] = 0.0;
   out_6762725012352014604[234] = 0.0;
   out_6762725012352014604[235] = 0.0;
   out_6762725012352014604[236] = 0.0;
   out_6762725012352014604[237] = 0.0;
   out_6762725012352014604[238] = 0.0;
   out_6762725012352014604[239] = 0.0;
   out_6762725012352014604[240] = 0.0;
   out_6762725012352014604[241] = 0.0;
   out_6762725012352014604[242] = 0.0;
   out_6762725012352014604[243] = 0.0;
   out_6762725012352014604[244] = 0.0;
   out_6762725012352014604[245] = 0.0;
   out_6762725012352014604[246] = 0.0;
   out_6762725012352014604[247] = 1.0;
   out_6762725012352014604[248] = 0.0;
   out_6762725012352014604[249] = 0.0;
   out_6762725012352014604[250] = 0.0;
   out_6762725012352014604[251] = 0.0;
   out_6762725012352014604[252] = 0.0;
   out_6762725012352014604[253] = 0.0;
   out_6762725012352014604[254] = 0.0;
   out_6762725012352014604[255] = 0.0;
   out_6762725012352014604[256] = 0.0;
   out_6762725012352014604[257] = 0.0;
   out_6762725012352014604[258] = 0.0;
   out_6762725012352014604[259] = 0.0;
   out_6762725012352014604[260] = 0.0;
   out_6762725012352014604[261] = 0.0;
   out_6762725012352014604[262] = 0.0;
   out_6762725012352014604[263] = 0.0;
   out_6762725012352014604[264] = 0.0;
   out_6762725012352014604[265] = 0.0;
   out_6762725012352014604[266] = 1.0;
   out_6762725012352014604[267] = 0.0;
   out_6762725012352014604[268] = 0.0;
   out_6762725012352014604[269] = 0.0;
   out_6762725012352014604[270] = 0.0;
   out_6762725012352014604[271] = 0.0;
   out_6762725012352014604[272] = 0.0;
   out_6762725012352014604[273] = 0.0;
   out_6762725012352014604[274] = 0.0;
   out_6762725012352014604[275] = 0.0;
   out_6762725012352014604[276] = 0.0;
   out_6762725012352014604[277] = 0.0;
   out_6762725012352014604[278] = 0.0;
   out_6762725012352014604[279] = 0.0;
   out_6762725012352014604[280] = 0.0;
   out_6762725012352014604[281] = 0.0;
   out_6762725012352014604[282] = 0.0;
   out_6762725012352014604[283] = 0.0;
   out_6762725012352014604[284] = 0.0;
   out_6762725012352014604[285] = 1.0;
   out_6762725012352014604[286] = 0.0;
   out_6762725012352014604[287] = 0.0;
   out_6762725012352014604[288] = 0.0;
   out_6762725012352014604[289] = 0.0;
   out_6762725012352014604[290] = 0.0;
   out_6762725012352014604[291] = 0.0;
   out_6762725012352014604[292] = 0.0;
   out_6762725012352014604[293] = 0.0;
   out_6762725012352014604[294] = 0.0;
   out_6762725012352014604[295] = 0.0;
   out_6762725012352014604[296] = 0.0;
   out_6762725012352014604[297] = 0.0;
   out_6762725012352014604[298] = 0.0;
   out_6762725012352014604[299] = 0.0;
   out_6762725012352014604[300] = 0.0;
   out_6762725012352014604[301] = 0.0;
   out_6762725012352014604[302] = 0.0;
   out_6762725012352014604[303] = 0.0;
   out_6762725012352014604[304] = 1.0;
   out_6762725012352014604[305] = 0.0;
   out_6762725012352014604[306] = 0.0;
   out_6762725012352014604[307] = 0.0;
   out_6762725012352014604[308] = 0.0;
   out_6762725012352014604[309] = 0.0;
   out_6762725012352014604[310] = 0.0;
   out_6762725012352014604[311] = 0.0;
   out_6762725012352014604[312] = 0.0;
   out_6762725012352014604[313] = 0.0;
   out_6762725012352014604[314] = 0.0;
   out_6762725012352014604[315] = 0.0;
   out_6762725012352014604[316] = 0.0;
   out_6762725012352014604[317] = 0.0;
   out_6762725012352014604[318] = 0.0;
   out_6762725012352014604[319] = 0.0;
   out_6762725012352014604[320] = 0.0;
   out_6762725012352014604[321] = 0.0;
   out_6762725012352014604[322] = 0.0;
   out_6762725012352014604[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_2890023609994291477) {
   out_2890023609994291477[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_2890023609994291477[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_2890023609994291477[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_2890023609994291477[3] = dt*state[12] + state[3];
   out_2890023609994291477[4] = dt*state[13] + state[4];
   out_2890023609994291477[5] = dt*state[14] + state[5];
   out_2890023609994291477[6] = state[6];
   out_2890023609994291477[7] = state[7];
   out_2890023609994291477[8] = state[8];
   out_2890023609994291477[9] = state[9];
   out_2890023609994291477[10] = state[10];
   out_2890023609994291477[11] = state[11];
   out_2890023609994291477[12] = state[12];
   out_2890023609994291477[13] = state[13];
   out_2890023609994291477[14] = state[14];
   out_2890023609994291477[15] = state[15];
   out_2890023609994291477[16] = state[16];
   out_2890023609994291477[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6035160646602114178) {
   out_6035160646602114178[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6035160646602114178[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6035160646602114178[2] = 0;
   out_6035160646602114178[3] = 0;
   out_6035160646602114178[4] = 0;
   out_6035160646602114178[5] = 0;
   out_6035160646602114178[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6035160646602114178[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6035160646602114178[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6035160646602114178[9] = 0;
   out_6035160646602114178[10] = 0;
   out_6035160646602114178[11] = 0;
   out_6035160646602114178[12] = 0;
   out_6035160646602114178[13] = 0;
   out_6035160646602114178[14] = 0;
   out_6035160646602114178[15] = 0;
   out_6035160646602114178[16] = 0;
   out_6035160646602114178[17] = 0;
   out_6035160646602114178[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6035160646602114178[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6035160646602114178[20] = 0;
   out_6035160646602114178[21] = 0;
   out_6035160646602114178[22] = 0;
   out_6035160646602114178[23] = 0;
   out_6035160646602114178[24] = 0;
   out_6035160646602114178[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6035160646602114178[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6035160646602114178[27] = 0;
   out_6035160646602114178[28] = 0;
   out_6035160646602114178[29] = 0;
   out_6035160646602114178[30] = 0;
   out_6035160646602114178[31] = 0;
   out_6035160646602114178[32] = 0;
   out_6035160646602114178[33] = 0;
   out_6035160646602114178[34] = 0;
   out_6035160646602114178[35] = 0;
   out_6035160646602114178[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6035160646602114178[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6035160646602114178[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6035160646602114178[39] = 0;
   out_6035160646602114178[40] = 0;
   out_6035160646602114178[41] = 0;
   out_6035160646602114178[42] = 0;
   out_6035160646602114178[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6035160646602114178[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6035160646602114178[45] = 0;
   out_6035160646602114178[46] = 0;
   out_6035160646602114178[47] = 0;
   out_6035160646602114178[48] = 0;
   out_6035160646602114178[49] = 0;
   out_6035160646602114178[50] = 0;
   out_6035160646602114178[51] = 0;
   out_6035160646602114178[52] = 0;
   out_6035160646602114178[53] = 0;
   out_6035160646602114178[54] = 0;
   out_6035160646602114178[55] = 0;
   out_6035160646602114178[56] = 0;
   out_6035160646602114178[57] = 1;
   out_6035160646602114178[58] = 0;
   out_6035160646602114178[59] = 0;
   out_6035160646602114178[60] = 0;
   out_6035160646602114178[61] = 0;
   out_6035160646602114178[62] = 0;
   out_6035160646602114178[63] = 0;
   out_6035160646602114178[64] = 0;
   out_6035160646602114178[65] = 0;
   out_6035160646602114178[66] = dt;
   out_6035160646602114178[67] = 0;
   out_6035160646602114178[68] = 0;
   out_6035160646602114178[69] = 0;
   out_6035160646602114178[70] = 0;
   out_6035160646602114178[71] = 0;
   out_6035160646602114178[72] = 0;
   out_6035160646602114178[73] = 0;
   out_6035160646602114178[74] = 0;
   out_6035160646602114178[75] = 0;
   out_6035160646602114178[76] = 1;
   out_6035160646602114178[77] = 0;
   out_6035160646602114178[78] = 0;
   out_6035160646602114178[79] = 0;
   out_6035160646602114178[80] = 0;
   out_6035160646602114178[81] = 0;
   out_6035160646602114178[82] = 0;
   out_6035160646602114178[83] = 0;
   out_6035160646602114178[84] = 0;
   out_6035160646602114178[85] = dt;
   out_6035160646602114178[86] = 0;
   out_6035160646602114178[87] = 0;
   out_6035160646602114178[88] = 0;
   out_6035160646602114178[89] = 0;
   out_6035160646602114178[90] = 0;
   out_6035160646602114178[91] = 0;
   out_6035160646602114178[92] = 0;
   out_6035160646602114178[93] = 0;
   out_6035160646602114178[94] = 0;
   out_6035160646602114178[95] = 1;
   out_6035160646602114178[96] = 0;
   out_6035160646602114178[97] = 0;
   out_6035160646602114178[98] = 0;
   out_6035160646602114178[99] = 0;
   out_6035160646602114178[100] = 0;
   out_6035160646602114178[101] = 0;
   out_6035160646602114178[102] = 0;
   out_6035160646602114178[103] = 0;
   out_6035160646602114178[104] = dt;
   out_6035160646602114178[105] = 0;
   out_6035160646602114178[106] = 0;
   out_6035160646602114178[107] = 0;
   out_6035160646602114178[108] = 0;
   out_6035160646602114178[109] = 0;
   out_6035160646602114178[110] = 0;
   out_6035160646602114178[111] = 0;
   out_6035160646602114178[112] = 0;
   out_6035160646602114178[113] = 0;
   out_6035160646602114178[114] = 1;
   out_6035160646602114178[115] = 0;
   out_6035160646602114178[116] = 0;
   out_6035160646602114178[117] = 0;
   out_6035160646602114178[118] = 0;
   out_6035160646602114178[119] = 0;
   out_6035160646602114178[120] = 0;
   out_6035160646602114178[121] = 0;
   out_6035160646602114178[122] = 0;
   out_6035160646602114178[123] = 0;
   out_6035160646602114178[124] = 0;
   out_6035160646602114178[125] = 0;
   out_6035160646602114178[126] = 0;
   out_6035160646602114178[127] = 0;
   out_6035160646602114178[128] = 0;
   out_6035160646602114178[129] = 0;
   out_6035160646602114178[130] = 0;
   out_6035160646602114178[131] = 0;
   out_6035160646602114178[132] = 0;
   out_6035160646602114178[133] = 1;
   out_6035160646602114178[134] = 0;
   out_6035160646602114178[135] = 0;
   out_6035160646602114178[136] = 0;
   out_6035160646602114178[137] = 0;
   out_6035160646602114178[138] = 0;
   out_6035160646602114178[139] = 0;
   out_6035160646602114178[140] = 0;
   out_6035160646602114178[141] = 0;
   out_6035160646602114178[142] = 0;
   out_6035160646602114178[143] = 0;
   out_6035160646602114178[144] = 0;
   out_6035160646602114178[145] = 0;
   out_6035160646602114178[146] = 0;
   out_6035160646602114178[147] = 0;
   out_6035160646602114178[148] = 0;
   out_6035160646602114178[149] = 0;
   out_6035160646602114178[150] = 0;
   out_6035160646602114178[151] = 0;
   out_6035160646602114178[152] = 1;
   out_6035160646602114178[153] = 0;
   out_6035160646602114178[154] = 0;
   out_6035160646602114178[155] = 0;
   out_6035160646602114178[156] = 0;
   out_6035160646602114178[157] = 0;
   out_6035160646602114178[158] = 0;
   out_6035160646602114178[159] = 0;
   out_6035160646602114178[160] = 0;
   out_6035160646602114178[161] = 0;
   out_6035160646602114178[162] = 0;
   out_6035160646602114178[163] = 0;
   out_6035160646602114178[164] = 0;
   out_6035160646602114178[165] = 0;
   out_6035160646602114178[166] = 0;
   out_6035160646602114178[167] = 0;
   out_6035160646602114178[168] = 0;
   out_6035160646602114178[169] = 0;
   out_6035160646602114178[170] = 0;
   out_6035160646602114178[171] = 1;
   out_6035160646602114178[172] = 0;
   out_6035160646602114178[173] = 0;
   out_6035160646602114178[174] = 0;
   out_6035160646602114178[175] = 0;
   out_6035160646602114178[176] = 0;
   out_6035160646602114178[177] = 0;
   out_6035160646602114178[178] = 0;
   out_6035160646602114178[179] = 0;
   out_6035160646602114178[180] = 0;
   out_6035160646602114178[181] = 0;
   out_6035160646602114178[182] = 0;
   out_6035160646602114178[183] = 0;
   out_6035160646602114178[184] = 0;
   out_6035160646602114178[185] = 0;
   out_6035160646602114178[186] = 0;
   out_6035160646602114178[187] = 0;
   out_6035160646602114178[188] = 0;
   out_6035160646602114178[189] = 0;
   out_6035160646602114178[190] = 1;
   out_6035160646602114178[191] = 0;
   out_6035160646602114178[192] = 0;
   out_6035160646602114178[193] = 0;
   out_6035160646602114178[194] = 0;
   out_6035160646602114178[195] = 0;
   out_6035160646602114178[196] = 0;
   out_6035160646602114178[197] = 0;
   out_6035160646602114178[198] = 0;
   out_6035160646602114178[199] = 0;
   out_6035160646602114178[200] = 0;
   out_6035160646602114178[201] = 0;
   out_6035160646602114178[202] = 0;
   out_6035160646602114178[203] = 0;
   out_6035160646602114178[204] = 0;
   out_6035160646602114178[205] = 0;
   out_6035160646602114178[206] = 0;
   out_6035160646602114178[207] = 0;
   out_6035160646602114178[208] = 0;
   out_6035160646602114178[209] = 1;
   out_6035160646602114178[210] = 0;
   out_6035160646602114178[211] = 0;
   out_6035160646602114178[212] = 0;
   out_6035160646602114178[213] = 0;
   out_6035160646602114178[214] = 0;
   out_6035160646602114178[215] = 0;
   out_6035160646602114178[216] = 0;
   out_6035160646602114178[217] = 0;
   out_6035160646602114178[218] = 0;
   out_6035160646602114178[219] = 0;
   out_6035160646602114178[220] = 0;
   out_6035160646602114178[221] = 0;
   out_6035160646602114178[222] = 0;
   out_6035160646602114178[223] = 0;
   out_6035160646602114178[224] = 0;
   out_6035160646602114178[225] = 0;
   out_6035160646602114178[226] = 0;
   out_6035160646602114178[227] = 0;
   out_6035160646602114178[228] = 1;
   out_6035160646602114178[229] = 0;
   out_6035160646602114178[230] = 0;
   out_6035160646602114178[231] = 0;
   out_6035160646602114178[232] = 0;
   out_6035160646602114178[233] = 0;
   out_6035160646602114178[234] = 0;
   out_6035160646602114178[235] = 0;
   out_6035160646602114178[236] = 0;
   out_6035160646602114178[237] = 0;
   out_6035160646602114178[238] = 0;
   out_6035160646602114178[239] = 0;
   out_6035160646602114178[240] = 0;
   out_6035160646602114178[241] = 0;
   out_6035160646602114178[242] = 0;
   out_6035160646602114178[243] = 0;
   out_6035160646602114178[244] = 0;
   out_6035160646602114178[245] = 0;
   out_6035160646602114178[246] = 0;
   out_6035160646602114178[247] = 1;
   out_6035160646602114178[248] = 0;
   out_6035160646602114178[249] = 0;
   out_6035160646602114178[250] = 0;
   out_6035160646602114178[251] = 0;
   out_6035160646602114178[252] = 0;
   out_6035160646602114178[253] = 0;
   out_6035160646602114178[254] = 0;
   out_6035160646602114178[255] = 0;
   out_6035160646602114178[256] = 0;
   out_6035160646602114178[257] = 0;
   out_6035160646602114178[258] = 0;
   out_6035160646602114178[259] = 0;
   out_6035160646602114178[260] = 0;
   out_6035160646602114178[261] = 0;
   out_6035160646602114178[262] = 0;
   out_6035160646602114178[263] = 0;
   out_6035160646602114178[264] = 0;
   out_6035160646602114178[265] = 0;
   out_6035160646602114178[266] = 1;
   out_6035160646602114178[267] = 0;
   out_6035160646602114178[268] = 0;
   out_6035160646602114178[269] = 0;
   out_6035160646602114178[270] = 0;
   out_6035160646602114178[271] = 0;
   out_6035160646602114178[272] = 0;
   out_6035160646602114178[273] = 0;
   out_6035160646602114178[274] = 0;
   out_6035160646602114178[275] = 0;
   out_6035160646602114178[276] = 0;
   out_6035160646602114178[277] = 0;
   out_6035160646602114178[278] = 0;
   out_6035160646602114178[279] = 0;
   out_6035160646602114178[280] = 0;
   out_6035160646602114178[281] = 0;
   out_6035160646602114178[282] = 0;
   out_6035160646602114178[283] = 0;
   out_6035160646602114178[284] = 0;
   out_6035160646602114178[285] = 1;
   out_6035160646602114178[286] = 0;
   out_6035160646602114178[287] = 0;
   out_6035160646602114178[288] = 0;
   out_6035160646602114178[289] = 0;
   out_6035160646602114178[290] = 0;
   out_6035160646602114178[291] = 0;
   out_6035160646602114178[292] = 0;
   out_6035160646602114178[293] = 0;
   out_6035160646602114178[294] = 0;
   out_6035160646602114178[295] = 0;
   out_6035160646602114178[296] = 0;
   out_6035160646602114178[297] = 0;
   out_6035160646602114178[298] = 0;
   out_6035160646602114178[299] = 0;
   out_6035160646602114178[300] = 0;
   out_6035160646602114178[301] = 0;
   out_6035160646602114178[302] = 0;
   out_6035160646602114178[303] = 0;
   out_6035160646602114178[304] = 1;
   out_6035160646602114178[305] = 0;
   out_6035160646602114178[306] = 0;
   out_6035160646602114178[307] = 0;
   out_6035160646602114178[308] = 0;
   out_6035160646602114178[309] = 0;
   out_6035160646602114178[310] = 0;
   out_6035160646602114178[311] = 0;
   out_6035160646602114178[312] = 0;
   out_6035160646602114178[313] = 0;
   out_6035160646602114178[314] = 0;
   out_6035160646602114178[315] = 0;
   out_6035160646602114178[316] = 0;
   out_6035160646602114178[317] = 0;
   out_6035160646602114178[318] = 0;
   out_6035160646602114178[319] = 0;
   out_6035160646602114178[320] = 0;
   out_6035160646602114178[321] = 0;
   out_6035160646602114178[322] = 0;
   out_6035160646602114178[323] = 1;
}
void h_4(double *state, double *unused, double *out_8808099240894619749) {
   out_8808099240894619749[0] = state[6] + state[9];
   out_8808099240894619749[1] = state[7] + state[10];
   out_8808099240894619749[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_4232559715645661926) {
   out_4232559715645661926[0] = 0;
   out_4232559715645661926[1] = 0;
   out_4232559715645661926[2] = 0;
   out_4232559715645661926[3] = 0;
   out_4232559715645661926[4] = 0;
   out_4232559715645661926[5] = 0;
   out_4232559715645661926[6] = 1;
   out_4232559715645661926[7] = 0;
   out_4232559715645661926[8] = 0;
   out_4232559715645661926[9] = 1;
   out_4232559715645661926[10] = 0;
   out_4232559715645661926[11] = 0;
   out_4232559715645661926[12] = 0;
   out_4232559715645661926[13] = 0;
   out_4232559715645661926[14] = 0;
   out_4232559715645661926[15] = 0;
   out_4232559715645661926[16] = 0;
   out_4232559715645661926[17] = 0;
   out_4232559715645661926[18] = 0;
   out_4232559715645661926[19] = 0;
   out_4232559715645661926[20] = 0;
   out_4232559715645661926[21] = 0;
   out_4232559715645661926[22] = 0;
   out_4232559715645661926[23] = 0;
   out_4232559715645661926[24] = 0;
   out_4232559715645661926[25] = 1;
   out_4232559715645661926[26] = 0;
   out_4232559715645661926[27] = 0;
   out_4232559715645661926[28] = 1;
   out_4232559715645661926[29] = 0;
   out_4232559715645661926[30] = 0;
   out_4232559715645661926[31] = 0;
   out_4232559715645661926[32] = 0;
   out_4232559715645661926[33] = 0;
   out_4232559715645661926[34] = 0;
   out_4232559715645661926[35] = 0;
   out_4232559715645661926[36] = 0;
   out_4232559715645661926[37] = 0;
   out_4232559715645661926[38] = 0;
   out_4232559715645661926[39] = 0;
   out_4232559715645661926[40] = 0;
   out_4232559715645661926[41] = 0;
   out_4232559715645661926[42] = 0;
   out_4232559715645661926[43] = 0;
   out_4232559715645661926[44] = 1;
   out_4232559715645661926[45] = 0;
   out_4232559715645661926[46] = 0;
   out_4232559715645661926[47] = 1;
   out_4232559715645661926[48] = 0;
   out_4232559715645661926[49] = 0;
   out_4232559715645661926[50] = 0;
   out_4232559715645661926[51] = 0;
   out_4232559715645661926[52] = 0;
   out_4232559715645661926[53] = 0;
}
void h_10(double *state, double *unused, double *out_7189369209365286749) {
   out_7189369209365286749[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7189369209365286749[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7189369209365286749[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_569566124478173203) {
   out_569566124478173203[0] = 0;
   out_569566124478173203[1] = 9.8100000000000005*cos(state[1]);
   out_569566124478173203[2] = 0;
   out_569566124478173203[3] = 0;
   out_569566124478173203[4] = -state[8];
   out_569566124478173203[5] = state[7];
   out_569566124478173203[6] = 0;
   out_569566124478173203[7] = state[5];
   out_569566124478173203[8] = -state[4];
   out_569566124478173203[9] = 0;
   out_569566124478173203[10] = 0;
   out_569566124478173203[11] = 0;
   out_569566124478173203[12] = 1;
   out_569566124478173203[13] = 0;
   out_569566124478173203[14] = 0;
   out_569566124478173203[15] = 1;
   out_569566124478173203[16] = 0;
   out_569566124478173203[17] = 0;
   out_569566124478173203[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_569566124478173203[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_569566124478173203[20] = 0;
   out_569566124478173203[21] = state[8];
   out_569566124478173203[22] = 0;
   out_569566124478173203[23] = -state[6];
   out_569566124478173203[24] = -state[5];
   out_569566124478173203[25] = 0;
   out_569566124478173203[26] = state[3];
   out_569566124478173203[27] = 0;
   out_569566124478173203[28] = 0;
   out_569566124478173203[29] = 0;
   out_569566124478173203[30] = 0;
   out_569566124478173203[31] = 1;
   out_569566124478173203[32] = 0;
   out_569566124478173203[33] = 0;
   out_569566124478173203[34] = 1;
   out_569566124478173203[35] = 0;
   out_569566124478173203[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_569566124478173203[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_569566124478173203[38] = 0;
   out_569566124478173203[39] = -state[7];
   out_569566124478173203[40] = state[6];
   out_569566124478173203[41] = 0;
   out_569566124478173203[42] = state[4];
   out_569566124478173203[43] = -state[3];
   out_569566124478173203[44] = 0;
   out_569566124478173203[45] = 0;
   out_569566124478173203[46] = 0;
   out_569566124478173203[47] = 0;
   out_569566124478173203[48] = 0;
   out_569566124478173203[49] = 0;
   out_569566124478173203[50] = 1;
   out_569566124478173203[51] = 0;
   out_569566124478173203[52] = 0;
   out_569566124478173203[53] = 1;
}
void h_13(double *state, double *unused, double *out_8915678619196498250) {
   out_8915678619196498250[0] = state[3];
   out_8915678619196498250[1] = state[4];
   out_8915678619196498250[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1020285890313329125) {
   out_1020285890313329125[0] = 0;
   out_1020285890313329125[1] = 0;
   out_1020285890313329125[2] = 0;
   out_1020285890313329125[3] = 1;
   out_1020285890313329125[4] = 0;
   out_1020285890313329125[5] = 0;
   out_1020285890313329125[6] = 0;
   out_1020285890313329125[7] = 0;
   out_1020285890313329125[8] = 0;
   out_1020285890313329125[9] = 0;
   out_1020285890313329125[10] = 0;
   out_1020285890313329125[11] = 0;
   out_1020285890313329125[12] = 0;
   out_1020285890313329125[13] = 0;
   out_1020285890313329125[14] = 0;
   out_1020285890313329125[15] = 0;
   out_1020285890313329125[16] = 0;
   out_1020285890313329125[17] = 0;
   out_1020285890313329125[18] = 0;
   out_1020285890313329125[19] = 0;
   out_1020285890313329125[20] = 0;
   out_1020285890313329125[21] = 0;
   out_1020285890313329125[22] = 1;
   out_1020285890313329125[23] = 0;
   out_1020285890313329125[24] = 0;
   out_1020285890313329125[25] = 0;
   out_1020285890313329125[26] = 0;
   out_1020285890313329125[27] = 0;
   out_1020285890313329125[28] = 0;
   out_1020285890313329125[29] = 0;
   out_1020285890313329125[30] = 0;
   out_1020285890313329125[31] = 0;
   out_1020285890313329125[32] = 0;
   out_1020285890313329125[33] = 0;
   out_1020285890313329125[34] = 0;
   out_1020285890313329125[35] = 0;
   out_1020285890313329125[36] = 0;
   out_1020285890313329125[37] = 0;
   out_1020285890313329125[38] = 0;
   out_1020285890313329125[39] = 0;
   out_1020285890313329125[40] = 0;
   out_1020285890313329125[41] = 1;
   out_1020285890313329125[42] = 0;
   out_1020285890313329125[43] = 0;
   out_1020285890313329125[44] = 0;
   out_1020285890313329125[45] = 0;
   out_1020285890313329125[46] = 0;
   out_1020285890313329125[47] = 0;
   out_1020285890313329125[48] = 0;
   out_1020285890313329125[49] = 0;
   out_1020285890313329125[50] = 0;
   out_1020285890313329125[51] = 0;
   out_1020285890313329125[52] = 0;
   out_1020285890313329125[53] = 0;
}
void h_14(double *state, double *unused, double *out_1817180151455941432) {
   out_1817180151455941432[0] = state[6];
   out_1817180151455941432[1] = state[7];
   out_1817180151455941432[2] = state[8];
}
void H_14(double *state, double *unused, double *out_269318859306177397) {
   out_269318859306177397[0] = 0;
   out_269318859306177397[1] = 0;
   out_269318859306177397[2] = 0;
   out_269318859306177397[3] = 0;
   out_269318859306177397[4] = 0;
   out_269318859306177397[5] = 0;
   out_269318859306177397[6] = 1;
   out_269318859306177397[7] = 0;
   out_269318859306177397[8] = 0;
   out_269318859306177397[9] = 0;
   out_269318859306177397[10] = 0;
   out_269318859306177397[11] = 0;
   out_269318859306177397[12] = 0;
   out_269318859306177397[13] = 0;
   out_269318859306177397[14] = 0;
   out_269318859306177397[15] = 0;
   out_269318859306177397[16] = 0;
   out_269318859306177397[17] = 0;
   out_269318859306177397[18] = 0;
   out_269318859306177397[19] = 0;
   out_269318859306177397[20] = 0;
   out_269318859306177397[21] = 0;
   out_269318859306177397[22] = 0;
   out_269318859306177397[23] = 0;
   out_269318859306177397[24] = 0;
   out_269318859306177397[25] = 1;
   out_269318859306177397[26] = 0;
   out_269318859306177397[27] = 0;
   out_269318859306177397[28] = 0;
   out_269318859306177397[29] = 0;
   out_269318859306177397[30] = 0;
   out_269318859306177397[31] = 0;
   out_269318859306177397[32] = 0;
   out_269318859306177397[33] = 0;
   out_269318859306177397[34] = 0;
   out_269318859306177397[35] = 0;
   out_269318859306177397[36] = 0;
   out_269318859306177397[37] = 0;
   out_269318859306177397[38] = 0;
   out_269318859306177397[39] = 0;
   out_269318859306177397[40] = 0;
   out_269318859306177397[41] = 0;
   out_269318859306177397[42] = 0;
   out_269318859306177397[43] = 0;
   out_269318859306177397[44] = 1;
   out_269318859306177397[45] = 0;
   out_269318859306177397[46] = 0;
   out_269318859306177397[47] = 0;
   out_269318859306177397[48] = 0;
   out_269318859306177397[49] = 0;
   out_269318859306177397[50] = 0;
   out_269318859306177397[51] = 0;
   out_269318859306177397[52] = 0;
   out_269318859306177397[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_1774761985787739244) {
  err_fun(nom_x, delta_x, out_1774761985787739244);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1588823582514134997) {
  inv_err_fun(nom_x, true_x, out_1588823582514134997);
}
void pose_H_mod_fun(double *state, double *out_6762725012352014604) {
  H_mod_fun(state, out_6762725012352014604);
}
void pose_f_fun(double *state, double dt, double *out_2890023609994291477) {
  f_fun(state,  dt, out_2890023609994291477);
}
void pose_F_fun(double *state, double dt, double *out_6035160646602114178) {
  F_fun(state,  dt, out_6035160646602114178);
}
void pose_h_4(double *state, double *unused, double *out_8808099240894619749) {
  h_4(state, unused, out_8808099240894619749);
}
void pose_H_4(double *state, double *unused, double *out_4232559715645661926) {
  H_4(state, unused, out_4232559715645661926);
}
void pose_h_10(double *state, double *unused, double *out_7189369209365286749) {
  h_10(state, unused, out_7189369209365286749);
}
void pose_H_10(double *state, double *unused, double *out_569566124478173203) {
  H_10(state, unused, out_569566124478173203);
}
void pose_h_13(double *state, double *unused, double *out_8915678619196498250) {
  h_13(state, unused, out_8915678619196498250);
}
void pose_H_13(double *state, double *unused, double *out_1020285890313329125) {
  H_13(state, unused, out_1020285890313329125);
}
void pose_h_14(double *state, double *unused, double *out_1817180151455941432) {
  h_14(state, unused, out_1817180151455941432);
}
void pose_H_14(double *state, double *unused, double *out_269318859306177397) {
  H_14(state, unused, out_269318859306177397);
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
