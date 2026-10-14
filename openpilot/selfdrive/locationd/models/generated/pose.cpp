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
void err_fun(double *nom_x, double *delta_x, double *out_7355263616721595469) {
   out_7355263616721595469[0] = delta_x[0] + nom_x[0];
   out_7355263616721595469[1] = delta_x[1] + nom_x[1];
   out_7355263616721595469[2] = delta_x[2] + nom_x[2];
   out_7355263616721595469[3] = delta_x[3] + nom_x[3];
   out_7355263616721595469[4] = delta_x[4] + nom_x[4];
   out_7355263616721595469[5] = delta_x[5] + nom_x[5];
   out_7355263616721595469[6] = delta_x[6] + nom_x[6];
   out_7355263616721595469[7] = delta_x[7] + nom_x[7];
   out_7355263616721595469[8] = delta_x[8] + nom_x[8];
   out_7355263616721595469[9] = delta_x[9] + nom_x[9];
   out_7355263616721595469[10] = delta_x[10] + nom_x[10];
   out_7355263616721595469[11] = delta_x[11] + nom_x[11];
   out_7355263616721595469[12] = delta_x[12] + nom_x[12];
   out_7355263616721595469[13] = delta_x[13] + nom_x[13];
   out_7355263616721595469[14] = delta_x[14] + nom_x[14];
   out_7355263616721595469[15] = delta_x[15] + nom_x[15];
   out_7355263616721595469[16] = delta_x[16] + nom_x[16];
   out_7355263616721595469[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8139235620588348311) {
   out_8139235620588348311[0] = -nom_x[0] + true_x[0];
   out_8139235620588348311[1] = -nom_x[1] + true_x[1];
   out_8139235620588348311[2] = -nom_x[2] + true_x[2];
   out_8139235620588348311[3] = -nom_x[3] + true_x[3];
   out_8139235620588348311[4] = -nom_x[4] + true_x[4];
   out_8139235620588348311[5] = -nom_x[5] + true_x[5];
   out_8139235620588348311[6] = -nom_x[6] + true_x[6];
   out_8139235620588348311[7] = -nom_x[7] + true_x[7];
   out_8139235620588348311[8] = -nom_x[8] + true_x[8];
   out_8139235620588348311[9] = -nom_x[9] + true_x[9];
   out_8139235620588348311[10] = -nom_x[10] + true_x[10];
   out_8139235620588348311[11] = -nom_x[11] + true_x[11];
   out_8139235620588348311[12] = -nom_x[12] + true_x[12];
   out_8139235620588348311[13] = -nom_x[13] + true_x[13];
   out_8139235620588348311[14] = -nom_x[14] + true_x[14];
   out_8139235620588348311[15] = -nom_x[15] + true_x[15];
   out_8139235620588348311[16] = -nom_x[16] + true_x[16];
   out_8139235620588348311[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7307874178124431266) {
   out_7307874178124431266[0] = 1.0;
   out_7307874178124431266[1] = 0.0;
   out_7307874178124431266[2] = 0.0;
   out_7307874178124431266[3] = 0.0;
   out_7307874178124431266[4] = 0.0;
   out_7307874178124431266[5] = 0.0;
   out_7307874178124431266[6] = 0.0;
   out_7307874178124431266[7] = 0.0;
   out_7307874178124431266[8] = 0.0;
   out_7307874178124431266[9] = 0.0;
   out_7307874178124431266[10] = 0.0;
   out_7307874178124431266[11] = 0.0;
   out_7307874178124431266[12] = 0.0;
   out_7307874178124431266[13] = 0.0;
   out_7307874178124431266[14] = 0.0;
   out_7307874178124431266[15] = 0.0;
   out_7307874178124431266[16] = 0.0;
   out_7307874178124431266[17] = 0.0;
   out_7307874178124431266[18] = 0.0;
   out_7307874178124431266[19] = 1.0;
   out_7307874178124431266[20] = 0.0;
   out_7307874178124431266[21] = 0.0;
   out_7307874178124431266[22] = 0.0;
   out_7307874178124431266[23] = 0.0;
   out_7307874178124431266[24] = 0.0;
   out_7307874178124431266[25] = 0.0;
   out_7307874178124431266[26] = 0.0;
   out_7307874178124431266[27] = 0.0;
   out_7307874178124431266[28] = 0.0;
   out_7307874178124431266[29] = 0.0;
   out_7307874178124431266[30] = 0.0;
   out_7307874178124431266[31] = 0.0;
   out_7307874178124431266[32] = 0.0;
   out_7307874178124431266[33] = 0.0;
   out_7307874178124431266[34] = 0.0;
   out_7307874178124431266[35] = 0.0;
   out_7307874178124431266[36] = 0.0;
   out_7307874178124431266[37] = 0.0;
   out_7307874178124431266[38] = 1.0;
   out_7307874178124431266[39] = 0.0;
   out_7307874178124431266[40] = 0.0;
   out_7307874178124431266[41] = 0.0;
   out_7307874178124431266[42] = 0.0;
   out_7307874178124431266[43] = 0.0;
   out_7307874178124431266[44] = 0.0;
   out_7307874178124431266[45] = 0.0;
   out_7307874178124431266[46] = 0.0;
   out_7307874178124431266[47] = 0.0;
   out_7307874178124431266[48] = 0.0;
   out_7307874178124431266[49] = 0.0;
   out_7307874178124431266[50] = 0.0;
   out_7307874178124431266[51] = 0.0;
   out_7307874178124431266[52] = 0.0;
   out_7307874178124431266[53] = 0.0;
   out_7307874178124431266[54] = 0.0;
   out_7307874178124431266[55] = 0.0;
   out_7307874178124431266[56] = 0.0;
   out_7307874178124431266[57] = 1.0;
   out_7307874178124431266[58] = 0.0;
   out_7307874178124431266[59] = 0.0;
   out_7307874178124431266[60] = 0.0;
   out_7307874178124431266[61] = 0.0;
   out_7307874178124431266[62] = 0.0;
   out_7307874178124431266[63] = 0.0;
   out_7307874178124431266[64] = 0.0;
   out_7307874178124431266[65] = 0.0;
   out_7307874178124431266[66] = 0.0;
   out_7307874178124431266[67] = 0.0;
   out_7307874178124431266[68] = 0.0;
   out_7307874178124431266[69] = 0.0;
   out_7307874178124431266[70] = 0.0;
   out_7307874178124431266[71] = 0.0;
   out_7307874178124431266[72] = 0.0;
   out_7307874178124431266[73] = 0.0;
   out_7307874178124431266[74] = 0.0;
   out_7307874178124431266[75] = 0.0;
   out_7307874178124431266[76] = 1.0;
   out_7307874178124431266[77] = 0.0;
   out_7307874178124431266[78] = 0.0;
   out_7307874178124431266[79] = 0.0;
   out_7307874178124431266[80] = 0.0;
   out_7307874178124431266[81] = 0.0;
   out_7307874178124431266[82] = 0.0;
   out_7307874178124431266[83] = 0.0;
   out_7307874178124431266[84] = 0.0;
   out_7307874178124431266[85] = 0.0;
   out_7307874178124431266[86] = 0.0;
   out_7307874178124431266[87] = 0.0;
   out_7307874178124431266[88] = 0.0;
   out_7307874178124431266[89] = 0.0;
   out_7307874178124431266[90] = 0.0;
   out_7307874178124431266[91] = 0.0;
   out_7307874178124431266[92] = 0.0;
   out_7307874178124431266[93] = 0.0;
   out_7307874178124431266[94] = 0.0;
   out_7307874178124431266[95] = 1.0;
   out_7307874178124431266[96] = 0.0;
   out_7307874178124431266[97] = 0.0;
   out_7307874178124431266[98] = 0.0;
   out_7307874178124431266[99] = 0.0;
   out_7307874178124431266[100] = 0.0;
   out_7307874178124431266[101] = 0.0;
   out_7307874178124431266[102] = 0.0;
   out_7307874178124431266[103] = 0.0;
   out_7307874178124431266[104] = 0.0;
   out_7307874178124431266[105] = 0.0;
   out_7307874178124431266[106] = 0.0;
   out_7307874178124431266[107] = 0.0;
   out_7307874178124431266[108] = 0.0;
   out_7307874178124431266[109] = 0.0;
   out_7307874178124431266[110] = 0.0;
   out_7307874178124431266[111] = 0.0;
   out_7307874178124431266[112] = 0.0;
   out_7307874178124431266[113] = 0.0;
   out_7307874178124431266[114] = 1.0;
   out_7307874178124431266[115] = 0.0;
   out_7307874178124431266[116] = 0.0;
   out_7307874178124431266[117] = 0.0;
   out_7307874178124431266[118] = 0.0;
   out_7307874178124431266[119] = 0.0;
   out_7307874178124431266[120] = 0.0;
   out_7307874178124431266[121] = 0.0;
   out_7307874178124431266[122] = 0.0;
   out_7307874178124431266[123] = 0.0;
   out_7307874178124431266[124] = 0.0;
   out_7307874178124431266[125] = 0.0;
   out_7307874178124431266[126] = 0.0;
   out_7307874178124431266[127] = 0.0;
   out_7307874178124431266[128] = 0.0;
   out_7307874178124431266[129] = 0.0;
   out_7307874178124431266[130] = 0.0;
   out_7307874178124431266[131] = 0.0;
   out_7307874178124431266[132] = 0.0;
   out_7307874178124431266[133] = 1.0;
   out_7307874178124431266[134] = 0.0;
   out_7307874178124431266[135] = 0.0;
   out_7307874178124431266[136] = 0.0;
   out_7307874178124431266[137] = 0.0;
   out_7307874178124431266[138] = 0.0;
   out_7307874178124431266[139] = 0.0;
   out_7307874178124431266[140] = 0.0;
   out_7307874178124431266[141] = 0.0;
   out_7307874178124431266[142] = 0.0;
   out_7307874178124431266[143] = 0.0;
   out_7307874178124431266[144] = 0.0;
   out_7307874178124431266[145] = 0.0;
   out_7307874178124431266[146] = 0.0;
   out_7307874178124431266[147] = 0.0;
   out_7307874178124431266[148] = 0.0;
   out_7307874178124431266[149] = 0.0;
   out_7307874178124431266[150] = 0.0;
   out_7307874178124431266[151] = 0.0;
   out_7307874178124431266[152] = 1.0;
   out_7307874178124431266[153] = 0.0;
   out_7307874178124431266[154] = 0.0;
   out_7307874178124431266[155] = 0.0;
   out_7307874178124431266[156] = 0.0;
   out_7307874178124431266[157] = 0.0;
   out_7307874178124431266[158] = 0.0;
   out_7307874178124431266[159] = 0.0;
   out_7307874178124431266[160] = 0.0;
   out_7307874178124431266[161] = 0.0;
   out_7307874178124431266[162] = 0.0;
   out_7307874178124431266[163] = 0.0;
   out_7307874178124431266[164] = 0.0;
   out_7307874178124431266[165] = 0.0;
   out_7307874178124431266[166] = 0.0;
   out_7307874178124431266[167] = 0.0;
   out_7307874178124431266[168] = 0.0;
   out_7307874178124431266[169] = 0.0;
   out_7307874178124431266[170] = 0.0;
   out_7307874178124431266[171] = 1.0;
   out_7307874178124431266[172] = 0.0;
   out_7307874178124431266[173] = 0.0;
   out_7307874178124431266[174] = 0.0;
   out_7307874178124431266[175] = 0.0;
   out_7307874178124431266[176] = 0.0;
   out_7307874178124431266[177] = 0.0;
   out_7307874178124431266[178] = 0.0;
   out_7307874178124431266[179] = 0.0;
   out_7307874178124431266[180] = 0.0;
   out_7307874178124431266[181] = 0.0;
   out_7307874178124431266[182] = 0.0;
   out_7307874178124431266[183] = 0.0;
   out_7307874178124431266[184] = 0.0;
   out_7307874178124431266[185] = 0.0;
   out_7307874178124431266[186] = 0.0;
   out_7307874178124431266[187] = 0.0;
   out_7307874178124431266[188] = 0.0;
   out_7307874178124431266[189] = 0.0;
   out_7307874178124431266[190] = 1.0;
   out_7307874178124431266[191] = 0.0;
   out_7307874178124431266[192] = 0.0;
   out_7307874178124431266[193] = 0.0;
   out_7307874178124431266[194] = 0.0;
   out_7307874178124431266[195] = 0.0;
   out_7307874178124431266[196] = 0.0;
   out_7307874178124431266[197] = 0.0;
   out_7307874178124431266[198] = 0.0;
   out_7307874178124431266[199] = 0.0;
   out_7307874178124431266[200] = 0.0;
   out_7307874178124431266[201] = 0.0;
   out_7307874178124431266[202] = 0.0;
   out_7307874178124431266[203] = 0.0;
   out_7307874178124431266[204] = 0.0;
   out_7307874178124431266[205] = 0.0;
   out_7307874178124431266[206] = 0.0;
   out_7307874178124431266[207] = 0.0;
   out_7307874178124431266[208] = 0.0;
   out_7307874178124431266[209] = 1.0;
   out_7307874178124431266[210] = 0.0;
   out_7307874178124431266[211] = 0.0;
   out_7307874178124431266[212] = 0.0;
   out_7307874178124431266[213] = 0.0;
   out_7307874178124431266[214] = 0.0;
   out_7307874178124431266[215] = 0.0;
   out_7307874178124431266[216] = 0.0;
   out_7307874178124431266[217] = 0.0;
   out_7307874178124431266[218] = 0.0;
   out_7307874178124431266[219] = 0.0;
   out_7307874178124431266[220] = 0.0;
   out_7307874178124431266[221] = 0.0;
   out_7307874178124431266[222] = 0.0;
   out_7307874178124431266[223] = 0.0;
   out_7307874178124431266[224] = 0.0;
   out_7307874178124431266[225] = 0.0;
   out_7307874178124431266[226] = 0.0;
   out_7307874178124431266[227] = 0.0;
   out_7307874178124431266[228] = 1.0;
   out_7307874178124431266[229] = 0.0;
   out_7307874178124431266[230] = 0.0;
   out_7307874178124431266[231] = 0.0;
   out_7307874178124431266[232] = 0.0;
   out_7307874178124431266[233] = 0.0;
   out_7307874178124431266[234] = 0.0;
   out_7307874178124431266[235] = 0.0;
   out_7307874178124431266[236] = 0.0;
   out_7307874178124431266[237] = 0.0;
   out_7307874178124431266[238] = 0.0;
   out_7307874178124431266[239] = 0.0;
   out_7307874178124431266[240] = 0.0;
   out_7307874178124431266[241] = 0.0;
   out_7307874178124431266[242] = 0.0;
   out_7307874178124431266[243] = 0.0;
   out_7307874178124431266[244] = 0.0;
   out_7307874178124431266[245] = 0.0;
   out_7307874178124431266[246] = 0.0;
   out_7307874178124431266[247] = 1.0;
   out_7307874178124431266[248] = 0.0;
   out_7307874178124431266[249] = 0.0;
   out_7307874178124431266[250] = 0.0;
   out_7307874178124431266[251] = 0.0;
   out_7307874178124431266[252] = 0.0;
   out_7307874178124431266[253] = 0.0;
   out_7307874178124431266[254] = 0.0;
   out_7307874178124431266[255] = 0.0;
   out_7307874178124431266[256] = 0.0;
   out_7307874178124431266[257] = 0.0;
   out_7307874178124431266[258] = 0.0;
   out_7307874178124431266[259] = 0.0;
   out_7307874178124431266[260] = 0.0;
   out_7307874178124431266[261] = 0.0;
   out_7307874178124431266[262] = 0.0;
   out_7307874178124431266[263] = 0.0;
   out_7307874178124431266[264] = 0.0;
   out_7307874178124431266[265] = 0.0;
   out_7307874178124431266[266] = 1.0;
   out_7307874178124431266[267] = 0.0;
   out_7307874178124431266[268] = 0.0;
   out_7307874178124431266[269] = 0.0;
   out_7307874178124431266[270] = 0.0;
   out_7307874178124431266[271] = 0.0;
   out_7307874178124431266[272] = 0.0;
   out_7307874178124431266[273] = 0.0;
   out_7307874178124431266[274] = 0.0;
   out_7307874178124431266[275] = 0.0;
   out_7307874178124431266[276] = 0.0;
   out_7307874178124431266[277] = 0.0;
   out_7307874178124431266[278] = 0.0;
   out_7307874178124431266[279] = 0.0;
   out_7307874178124431266[280] = 0.0;
   out_7307874178124431266[281] = 0.0;
   out_7307874178124431266[282] = 0.0;
   out_7307874178124431266[283] = 0.0;
   out_7307874178124431266[284] = 0.0;
   out_7307874178124431266[285] = 1.0;
   out_7307874178124431266[286] = 0.0;
   out_7307874178124431266[287] = 0.0;
   out_7307874178124431266[288] = 0.0;
   out_7307874178124431266[289] = 0.0;
   out_7307874178124431266[290] = 0.0;
   out_7307874178124431266[291] = 0.0;
   out_7307874178124431266[292] = 0.0;
   out_7307874178124431266[293] = 0.0;
   out_7307874178124431266[294] = 0.0;
   out_7307874178124431266[295] = 0.0;
   out_7307874178124431266[296] = 0.0;
   out_7307874178124431266[297] = 0.0;
   out_7307874178124431266[298] = 0.0;
   out_7307874178124431266[299] = 0.0;
   out_7307874178124431266[300] = 0.0;
   out_7307874178124431266[301] = 0.0;
   out_7307874178124431266[302] = 0.0;
   out_7307874178124431266[303] = 0.0;
   out_7307874178124431266[304] = 1.0;
   out_7307874178124431266[305] = 0.0;
   out_7307874178124431266[306] = 0.0;
   out_7307874178124431266[307] = 0.0;
   out_7307874178124431266[308] = 0.0;
   out_7307874178124431266[309] = 0.0;
   out_7307874178124431266[310] = 0.0;
   out_7307874178124431266[311] = 0.0;
   out_7307874178124431266[312] = 0.0;
   out_7307874178124431266[313] = 0.0;
   out_7307874178124431266[314] = 0.0;
   out_7307874178124431266[315] = 0.0;
   out_7307874178124431266[316] = 0.0;
   out_7307874178124431266[317] = 0.0;
   out_7307874178124431266[318] = 0.0;
   out_7307874178124431266[319] = 0.0;
   out_7307874178124431266[320] = 0.0;
   out_7307874178124431266[321] = 0.0;
   out_7307874178124431266[322] = 0.0;
   out_7307874178124431266[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5281617793051128066) {
   out_5281617793051128066[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5281617793051128066[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5281617793051128066[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5281617793051128066[3] = dt*state[12] + state[3];
   out_5281617793051128066[4] = dt*state[13] + state[4];
   out_5281617793051128066[5] = dt*state[14] + state[5];
   out_5281617793051128066[6] = state[6];
   out_5281617793051128066[7] = state[7];
   out_5281617793051128066[8] = state[8];
   out_5281617793051128066[9] = state[9];
   out_5281617793051128066[10] = state[10];
   out_5281617793051128066[11] = state[11];
   out_5281617793051128066[12] = state[12];
   out_5281617793051128066[13] = state[13];
   out_5281617793051128066[14] = state[14];
   out_5281617793051128066[15] = state[15];
   out_5281617793051128066[16] = state[16];
   out_5281617793051128066[17] = state[17];
}
void F_fun(double *state, double dt, double *out_171852704988817231) {
   out_171852704988817231[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_171852704988817231[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_171852704988817231[2] = 0;
   out_171852704988817231[3] = 0;
   out_171852704988817231[4] = 0;
   out_171852704988817231[5] = 0;
   out_171852704988817231[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_171852704988817231[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_171852704988817231[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_171852704988817231[9] = 0;
   out_171852704988817231[10] = 0;
   out_171852704988817231[11] = 0;
   out_171852704988817231[12] = 0;
   out_171852704988817231[13] = 0;
   out_171852704988817231[14] = 0;
   out_171852704988817231[15] = 0;
   out_171852704988817231[16] = 0;
   out_171852704988817231[17] = 0;
   out_171852704988817231[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_171852704988817231[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_171852704988817231[20] = 0;
   out_171852704988817231[21] = 0;
   out_171852704988817231[22] = 0;
   out_171852704988817231[23] = 0;
   out_171852704988817231[24] = 0;
   out_171852704988817231[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_171852704988817231[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_171852704988817231[27] = 0;
   out_171852704988817231[28] = 0;
   out_171852704988817231[29] = 0;
   out_171852704988817231[30] = 0;
   out_171852704988817231[31] = 0;
   out_171852704988817231[32] = 0;
   out_171852704988817231[33] = 0;
   out_171852704988817231[34] = 0;
   out_171852704988817231[35] = 0;
   out_171852704988817231[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_171852704988817231[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_171852704988817231[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_171852704988817231[39] = 0;
   out_171852704988817231[40] = 0;
   out_171852704988817231[41] = 0;
   out_171852704988817231[42] = 0;
   out_171852704988817231[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_171852704988817231[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_171852704988817231[45] = 0;
   out_171852704988817231[46] = 0;
   out_171852704988817231[47] = 0;
   out_171852704988817231[48] = 0;
   out_171852704988817231[49] = 0;
   out_171852704988817231[50] = 0;
   out_171852704988817231[51] = 0;
   out_171852704988817231[52] = 0;
   out_171852704988817231[53] = 0;
   out_171852704988817231[54] = 0;
   out_171852704988817231[55] = 0;
   out_171852704988817231[56] = 0;
   out_171852704988817231[57] = 1;
   out_171852704988817231[58] = 0;
   out_171852704988817231[59] = 0;
   out_171852704988817231[60] = 0;
   out_171852704988817231[61] = 0;
   out_171852704988817231[62] = 0;
   out_171852704988817231[63] = 0;
   out_171852704988817231[64] = 0;
   out_171852704988817231[65] = 0;
   out_171852704988817231[66] = dt;
   out_171852704988817231[67] = 0;
   out_171852704988817231[68] = 0;
   out_171852704988817231[69] = 0;
   out_171852704988817231[70] = 0;
   out_171852704988817231[71] = 0;
   out_171852704988817231[72] = 0;
   out_171852704988817231[73] = 0;
   out_171852704988817231[74] = 0;
   out_171852704988817231[75] = 0;
   out_171852704988817231[76] = 1;
   out_171852704988817231[77] = 0;
   out_171852704988817231[78] = 0;
   out_171852704988817231[79] = 0;
   out_171852704988817231[80] = 0;
   out_171852704988817231[81] = 0;
   out_171852704988817231[82] = 0;
   out_171852704988817231[83] = 0;
   out_171852704988817231[84] = 0;
   out_171852704988817231[85] = dt;
   out_171852704988817231[86] = 0;
   out_171852704988817231[87] = 0;
   out_171852704988817231[88] = 0;
   out_171852704988817231[89] = 0;
   out_171852704988817231[90] = 0;
   out_171852704988817231[91] = 0;
   out_171852704988817231[92] = 0;
   out_171852704988817231[93] = 0;
   out_171852704988817231[94] = 0;
   out_171852704988817231[95] = 1;
   out_171852704988817231[96] = 0;
   out_171852704988817231[97] = 0;
   out_171852704988817231[98] = 0;
   out_171852704988817231[99] = 0;
   out_171852704988817231[100] = 0;
   out_171852704988817231[101] = 0;
   out_171852704988817231[102] = 0;
   out_171852704988817231[103] = 0;
   out_171852704988817231[104] = dt;
   out_171852704988817231[105] = 0;
   out_171852704988817231[106] = 0;
   out_171852704988817231[107] = 0;
   out_171852704988817231[108] = 0;
   out_171852704988817231[109] = 0;
   out_171852704988817231[110] = 0;
   out_171852704988817231[111] = 0;
   out_171852704988817231[112] = 0;
   out_171852704988817231[113] = 0;
   out_171852704988817231[114] = 1;
   out_171852704988817231[115] = 0;
   out_171852704988817231[116] = 0;
   out_171852704988817231[117] = 0;
   out_171852704988817231[118] = 0;
   out_171852704988817231[119] = 0;
   out_171852704988817231[120] = 0;
   out_171852704988817231[121] = 0;
   out_171852704988817231[122] = 0;
   out_171852704988817231[123] = 0;
   out_171852704988817231[124] = 0;
   out_171852704988817231[125] = 0;
   out_171852704988817231[126] = 0;
   out_171852704988817231[127] = 0;
   out_171852704988817231[128] = 0;
   out_171852704988817231[129] = 0;
   out_171852704988817231[130] = 0;
   out_171852704988817231[131] = 0;
   out_171852704988817231[132] = 0;
   out_171852704988817231[133] = 1;
   out_171852704988817231[134] = 0;
   out_171852704988817231[135] = 0;
   out_171852704988817231[136] = 0;
   out_171852704988817231[137] = 0;
   out_171852704988817231[138] = 0;
   out_171852704988817231[139] = 0;
   out_171852704988817231[140] = 0;
   out_171852704988817231[141] = 0;
   out_171852704988817231[142] = 0;
   out_171852704988817231[143] = 0;
   out_171852704988817231[144] = 0;
   out_171852704988817231[145] = 0;
   out_171852704988817231[146] = 0;
   out_171852704988817231[147] = 0;
   out_171852704988817231[148] = 0;
   out_171852704988817231[149] = 0;
   out_171852704988817231[150] = 0;
   out_171852704988817231[151] = 0;
   out_171852704988817231[152] = 1;
   out_171852704988817231[153] = 0;
   out_171852704988817231[154] = 0;
   out_171852704988817231[155] = 0;
   out_171852704988817231[156] = 0;
   out_171852704988817231[157] = 0;
   out_171852704988817231[158] = 0;
   out_171852704988817231[159] = 0;
   out_171852704988817231[160] = 0;
   out_171852704988817231[161] = 0;
   out_171852704988817231[162] = 0;
   out_171852704988817231[163] = 0;
   out_171852704988817231[164] = 0;
   out_171852704988817231[165] = 0;
   out_171852704988817231[166] = 0;
   out_171852704988817231[167] = 0;
   out_171852704988817231[168] = 0;
   out_171852704988817231[169] = 0;
   out_171852704988817231[170] = 0;
   out_171852704988817231[171] = 1;
   out_171852704988817231[172] = 0;
   out_171852704988817231[173] = 0;
   out_171852704988817231[174] = 0;
   out_171852704988817231[175] = 0;
   out_171852704988817231[176] = 0;
   out_171852704988817231[177] = 0;
   out_171852704988817231[178] = 0;
   out_171852704988817231[179] = 0;
   out_171852704988817231[180] = 0;
   out_171852704988817231[181] = 0;
   out_171852704988817231[182] = 0;
   out_171852704988817231[183] = 0;
   out_171852704988817231[184] = 0;
   out_171852704988817231[185] = 0;
   out_171852704988817231[186] = 0;
   out_171852704988817231[187] = 0;
   out_171852704988817231[188] = 0;
   out_171852704988817231[189] = 0;
   out_171852704988817231[190] = 1;
   out_171852704988817231[191] = 0;
   out_171852704988817231[192] = 0;
   out_171852704988817231[193] = 0;
   out_171852704988817231[194] = 0;
   out_171852704988817231[195] = 0;
   out_171852704988817231[196] = 0;
   out_171852704988817231[197] = 0;
   out_171852704988817231[198] = 0;
   out_171852704988817231[199] = 0;
   out_171852704988817231[200] = 0;
   out_171852704988817231[201] = 0;
   out_171852704988817231[202] = 0;
   out_171852704988817231[203] = 0;
   out_171852704988817231[204] = 0;
   out_171852704988817231[205] = 0;
   out_171852704988817231[206] = 0;
   out_171852704988817231[207] = 0;
   out_171852704988817231[208] = 0;
   out_171852704988817231[209] = 1;
   out_171852704988817231[210] = 0;
   out_171852704988817231[211] = 0;
   out_171852704988817231[212] = 0;
   out_171852704988817231[213] = 0;
   out_171852704988817231[214] = 0;
   out_171852704988817231[215] = 0;
   out_171852704988817231[216] = 0;
   out_171852704988817231[217] = 0;
   out_171852704988817231[218] = 0;
   out_171852704988817231[219] = 0;
   out_171852704988817231[220] = 0;
   out_171852704988817231[221] = 0;
   out_171852704988817231[222] = 0;
   out_171852704988817231[223] = 0;
   out_171852704988817231[224] = 0;
   out_171852704988817231[225] = 0;
   out_171852704988817231[226] = 0;
   out_171852704988817231[227] = 0;
   out_171852704988817231[228] = 1;
   out_171852704988817231[229] = 0;
   out_171852704988817231[230] = 0;
   out_171852704988817231[231] = 0;
   out_171852704988817231[232] = 0;
   out_171852704988817231[233] = 0;
   out_171852704988817231[234] = 0;
   out_171852704988817231[235] = 0;
   out_171852704988817231[236] = 0;
   out_171852704988817231[237] = 0;
   out_171852704988817231[238] = 0;
   out_171852704988817231[239] = 0;
   out_171852704988817231[240] = 0;
   out_171852704988817231[241] = 0;
   out_171852704988817231[242] = 0;
   out_171852704988817231[243] = 0;
   out_171852704988817231[244] = 0;
   out_171852704988817231[245] = 0;
   out_171852704988817231[246] = 0;
   out_171852704988817231[247] = 1;
   out_171852704988817231[248] = 0;
   out_171852704988817231[249] = 0;
   out_171852704988817231[250] = 0;
   out_171852704988817231[251] = 0;
   out_171852704988817231[252] = 0;
   out_171852704988817231[253] = 0;
   out_171852704988817231[254] = 0;
   out_171852704988817231[255] = 0;
   out_171852704988817231[256] = 0;
   out_171852704988817231[257] = 0;
   out_171852704988817231[258] = 0;
   out_171852704988817231[259] = 0;
   out_171852704988817231[260] = 0;
   out_171852704988817231[261] = 0;
   out_171852704988817231[262] = 0;
   out_171852704988817231[263] = 0;
   out_171852704988817231[264] = 0;
   out_171852704988817231[265] = 0;
   out_171852704988817231[266] = 1;
   out_171852704988817231[267] = 0;
   out_171852704988817231[268] = 0;
   out_171852704988817231[269] = 0;
   out_171852704988817231[270] = 0;
   out_171852704988817231[271] = 0;
   out_171852704988817231[272] = 0;
   out_171852704988817231[273] = 0;
   out_171852704988817231[274] = 0;
   out_171852704988817231[275] = 0;
   out_171852704988817231[276] = 0;
   out_171852704988817231[277] = 0;
   out_171852704988817231[278] = 0;
   out_171852704988817231[279] = 0;
   out_171852704988817231[280] = 0;
   out_171852704988817231[281] = 0;
   out_171852704988817231[282] = 0;
   out_171852704988817231[283] = 0;
   out_171852704988817231[284] = 0;
   out_171852704988817231[285] = 1;
   out_171852704988817231[286] = 0;
   out_171852704988817231[287] = 0;
   out_171852704988817231[288] = 0;
   out_171852704988817231[289] = 0;
   out_171852704988817231[290] = 0;
   out_171852704988817231[291] = 0;
   out_171852704988817231[292] = 0;
   out_171852704988817231[293] = 0;
   out_171852704988817231[294] = 0;
   out_171852704988817231[295] = 0;
   out_171852704988817231[296] = 0;
   out_171852704988817231[297] = 0;
   out_171852704988817231[298] = 0;
   out_171852704988817231[299] = 0;
   out_171852704988817231[300] = 0;
   out_171852704988817231[301] = 0;
   out_171852704988817231[302] = 0;
   out_171852704988817231[303] = 0;
   out_171852704988817231[304] = 1;
   out_171852704988817231[305] = 0;
   out_171852704988817231[306] = 0;
   out_171852704988817231[307] = 0;
   out_171852704988817231[308] = 0;
   out_171852704988817231[309] = 0;
   out_171852704988817231[310] = 0;
   out_171852704988817231[311] = 0;
   out_171852704988817231[312] = 0;
   out_171852704988817231[313] = 0;
   out_171852704988817231[314] = 0;
   out_171852704988817231[315] = 0;
   out_171852704988817231[316] = 0;
   out_171852704988817231[317] = 0;
   out_171852704988817231[318] = 0;
   out_171852704988817231[319] = 0;
   out_171852704988817231[320] = 0;
   out_171852704988817231[321] = 0;
   out_171852704988817231[322] = 0;
   out_171852704988817231[323] = 1;
}
void h_4(double *state, double *unused, double *out_2569970869827434637) {
   out_2569970869827434637[0] = state[6] + state[9];
   out_2569970869827434637[1] = state[7] + state[10];
   out_2569970869827434637[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8432009482317850141) {
   out_8432009482317850141[0] = 0;
   out_8432009482317850141[1] = 0;
   out_8432009482317850141[2] = 0;
   out_8432009482317850141[3] = 0;
   out_8432009482317850141[4] = 0;
   out_8432009482317850141[5] = 0;
   out_8432009482317850141[6] = 1;
   out_8432009482317850141[7] = 0;
   out_8432009482317850141[8] = 0;
   out_8432009482317850141[9] = 1;
   out_8432009482317850141[10] = 0;
   out_8432009482317850141[11] = 0;
   out_8432009482317850141[12] = 0;
   out_8432009482317850141[13] = 0;
   out_8432009482317850141[14] = 0;
   out_8432009482317850141[15] = 0;
   out_8432009482317850141[16] = 0;
   out_8432009482317850141[17] = 0;
   out_8432009482317850141[18] = 0;
   out_8432009482317850141[19] = 0;
   out_8432009482317850141[20] = 0;
   out_8432009482317850141[21] = 0;
   out_8432009482317850141[22] = 0;
   out_8432009482317850141[23] = 0;
   out_8432009482317850141[24] = 0;
   out_8432009482317850141[25] = 1;
   out_8432009482317850141[26] = 0;
   out_8432009482317850141[27] = 0;
   out_8432009482317850141[28] = 1;
   out_8432009482317850141[29] = 0;
   out_8432009482317850141[30] = 0;
   out_8432009482317850141[31] = 0;
   out_8432009482317850141[32] = 0;
   out_8432009482317850141[33] = 0;
   out_8432009482317850141[34] = 0;
   out_8432009482317850141[35] = 0;
   out_8432009482317850141[36] = 0;
   out_8432009482317850141[37] = 0;
   out_8432009482317850141[38] = 0;
   out_8432009482317850141[39] = 0;
   out_8432009482317850141[40] = 0;
   out_8432009482317850141[41] = 0;
   out_8432009482317850141[42] = 0;
   out_8432009482317850141[43] = 0;
   out_8432009482317850141[44] = 1;
   out_8432009482317850141[45] = 0;
   out_8432009482317850141[46] = 0;
   out_8432009482317850141[47] = 1;
   out_8432009482317850141[48] = 0;
   out_8432009482317850141[49] = 0;
   out_8432009482317850141[50] = 0;
   out_8432009482317850141[51] = 0;
   out_8432009482317850141[52] = 0;
   out_8432009482317850141[53] = 0;
}
void h_10(double *state, double *unused, double *out_3771666334899656059) {
   out_3771666334899656059[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3771666334899656059[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3771666334899656059[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_783655174248384591) {
   out_783655174248384591[0] = 0;
   out_783655174248384591[1] = 9.8100000000000005*cos(state[1]);
   out_783655174248384591[2] = 0;
   out_783655174248384591[3] = 0;
   out_783655174248384591[4] = -state[8];
   out_783655174248384591[5] = state[7];
   out_783655174248384591[6] = 0;
   out_783655174248384591[7] = state[5];
   out_783655174248384591[8] = -state[4];
   out_783655174248384591[9] = 0;
   out_783655174248384591[10] = 0;
   out_783655174248384591[11] = 0;
   out_783655174248384591[12] = 1;
   out_783655174248384591[13] = 0;
   out_783655174248384591[14] = 0;
   out_783655174248384591[15] = 1;
   out_783655174248384591[16] = 0;
   out_783655174248384591[17] = 0;
   out_783655174248384591[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_783655174248384591[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_783655174248384591[20] = 0;
   out_783655174248384591[21] = state[8];
   out_783655174248384591[22] = 0;
   out_783655174248384591[23] = -state[6];
   out_783655174248384591[24] = -state[5];
   out_783655174248384591[25] = 0;
   out_783655174248384591[26] = state[3];
   out_783655174248384591[27] = 0;
   out_783655174248384591[28] = 0;
   out_783655174248384591[29] = 0;
   out_783655174248384591[30] = 0;
   out_783655174248384591[31] = 1;
   out_783655174248384591[32] = 0;
   out_783655174248384591[33] = 0;
   out_783655174248384591[34] = 1;
   out_783655174248384591[35] = 0;
   out_783655174248384591[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_783655174248384591[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_783655174248384591[38] = 0;
   out_783655174248384591[39] = -state[7];
   out_783655174248384591[40] = state[6];
   out_783655174248384591[41] = 0;
   out_783655174248384591[42] = state[4];
   out_783655174248384591[43] = -state[3];
   out_783655174248384591[44] = 0;
   out_783655174248384591[45] = 0;
   out_783655174248384591[46] = 0;
   out_783655174248384591[47] = 0;
   out_783655174248384591[48] = 0;
   out_783655174248384591[49] = 0;
   out_783655174248384591[50] = 1;
   out_783655174248384591[51] = 0;
   out_783655174248384591[52] = 0;
   out_783655174248384591[53] = 1;
}
void h_13(double *state, double *unused, double *out_2343495232075740300) {
   out_2343495232075740300[0] = state[3];
   out_2343495232075740300[1] = state[4];
   out_2343495232075740300[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6802460766059368674) {
   out_6802460766059368674[0] = 0;
   out_6802460766059368674[1] = 0;
   out_6802460766059368674[2] = 0;
   out_6802460766059368674[3] = 1;
   out_6802460766059368674[4] = 0;
   out_6802460766059368674[5] = 0;
   out_6802460766059368674[6] = 0;
   out_6802460766059368674[7] = 0;
   out_6802460766059368674[8] = 0;
   out_6802460766059368674[9] = 0;
   out_6802460766059368674[10] = 0;
   out_6802460766059368674[11] = 0;
   out_6802460766059368674[12] = 0;
   out_6802460766059368674[13] = 0;
   out_6802460766059368674[14] = 0;
   out_6802460766059368674[15] = 0;
   out_6802460766059368674[16] = 0;
   out_6802460766059368674[17] = 0;
   out_6802460766059368674[18] = 0;
   out_6802460766059368674[19] = 0;
   out_6802460766059368674[20] = 0;
   out_6802460766059368674[21] = 0;
   out_6802460766059368674[22] = 1;
   out_6802460766059368674[23] = 0;
   out_6802460766059368674[24] = 0;
   out_6802460766059368674[25] = 0;
   out_6802460766059368674[26] = 0;
   out_6802460766059368674[27] = 0;
   out_6802460766059368674[28] = 0;
   out_6802460766059368674[29] = 0;
   out_6802460766059368674[30] = 0;
   out_6802460766059368674[31] = 0;
   out_6802460766059368674[32] = 0;
   out_6802460766059368674[33] = 0;
   out_6802460766059368674[34] = 0;
   out_6802460766059368674[35] = 0;
   out_6802460766059368674[36] = 0;
   out_6802460766059368674[37] = 0;
   out_6802460766059368674[38] = 0;
   out_6802460766059368674[39] = 0;
   out_6802460766059368674[40] = 0;
   out_6802460766059368674[41] = 1;
   out_6802460766059368674[42] = 0;
   out_6802460766059368674[43] = 0;
   out_6802460766059368674[44] = 0;
   out_6802460766059368674[45] = 0;
   out_6802460766059368674[46] = 0;
   out_6802460766059368674[47] = 0;
   out_6802460766059368674[48] = 0;
   out_6802460766059368674[49] = 0;
   out_6802460766059368674[50] = 0;
   out_6802460766059368674[51] = 0;
   out_6802460766059368674[52] = 0;
   out_6802460766059368674[53] = 0;
}
void h_14(double *state, double *unused, double *out_8726156210581630392) {
   out_8726156210581630392[0] = state[6];
   out_8726156210581630392[1] = state[7];
   out_8726156210581630392[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7996892955672966542) {
   out_7996892955672966542[0] = 0;
   out_7996892955672966542[1] = 0;
   out_7996892955672966542[2] = 0;
   out_7996892955672966542[3] = 0;
   out_7996892955672966542[4] = 0;
   out_7996892955672966542[5] = 0;
   out_7996892955672966542[6] = 1;
   out_7996892955672966542[7] = 0;
   out_7996892955672966542[8] = 0;
   out_7996892955672966542[9] = 0;
   out_7996892955672966542[10] = 0;
   out_7996892955672966542[11] = 0;
   out_7996892955672966542[12] = 0;
   out_7996892955672966542[13] = 0;
   out_7996892955672966542[14] = 0;
   out_7996892955672966542[15] = 0;
   out_7996892955672966542[16] = 0;
   out_7996892955672966542[17] = 0;
   out_7996892955672966542[18] = 0;
   out_7996892955672966542[19] = 0;
   out_7996892955672966542[20] = 0;
   out_7996892955672966542[21] = 0;
   out_7996892955672966542[22] = 0;
   out_7996892955672966542[23] = 0;
   out_7996892955672966542[24] = 0;
   out_7996892955672966542[25] = 1;
   out_7996892955672966542[26] = 0;
   out_7996892955672966542[27] = 0;
   out_7996892955672966542[28] = 0;
   out_7996892955672966542[29] = 0;
   out_7996892955672966542[30] = 0;
   out_7996892955672966542[31] = 0;
   out_7996892955672966542[32] = 0;
   out_7996892955672966542[33] = 0;
   out_7996892955672966542[34] = 0;
   out_7996892955672966542[35] = 0;
   out_7996892955672966542[36] = 0;
   out_7996892955672966542[37] = 0;
   out_7996892955672966542[38] = 0;
   out_7996892955672966542[39] = 0;
   out_7996892955672966542[40] = 0;
   out_7996892955672966542[41] = 0;
   out_7996892955672966542[42] = 0;
   out_7996892955672966542[43] = 0;
   out_7996892955672966542[44] = 1;
   out_7996892955672966542[45] = 0;
   out_7996892955672966542[46] = 0;
   out_7996892955672966542[47] = 0;
   out_7996892955672966542[48] = 0;
   out_7996892955672966542[49] = 0;
   out_7996892955672966542[50] = 0;
   out_7996892955672966542[51] = 0;
   out_7996892955672966542[52] = 0;
   out_7996892955672966542[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7355263616721595469) {
  err_fun(nom_x, delta_x, out_7355263616721595469);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8139235620588348311) {
  inv_err_fun(nom_x, true_x, out_8139235620588348311);
}
void pose_H_mod_fun(double *state, double *out_7307874178124431266) {
  H_mod_fun(state, out_7307874178124431266);
}
void pose_f_fun(double *state, double dt, double *out_5281617793051128066) {
  f_fun(state,  dt, out_5281617793051128066);
}
void pose_F_fun(double *state, double dt, double *out_171852704988817231) {
  F_fun(state,  dt, out_171852704988817231);
}
void pose_h_4(double *state, double *unused, double *out_2569970869827434637) {
  h_4(state, unused, out_2569970869827434637);
}
void pose_H_4(double *state, double *unused, double *out_8432009482317850141) {
  H_4(state, unused, out_8432009482317850141);
}
void pose_h_10(double *state, double *unused, double *out_3771666334899656059) {
  h_10(state, unused, out_3771666334899656059);
}
void pose_H_10(double *state, double *unused, double *out_783655174248384591) {
  H_10(state, unused, out_783655174248384591);
}
void pose_h_13(double *state, double *unused, double *out_2343495232075740300) {
  h_13(state, unused, out_2343495232075740300);
}
void pose_H_13(double *state, double *unused, double *out_6802460766059368674) {
  H_13(state, unused, out_6802460766059368674);
}
void pose_h_14(double *state, double *unused, double *out_8726156210581630392) {
  h_14(state, unused, out_8726156210581630392);
}
void pose_H_14(double *state, double *unused, double *out_7996892955672966542) {
  H_14(state, unused, out_7996892955672966542);
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
