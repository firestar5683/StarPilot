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
void err_fun(double *nom_x, double *delta_x, double *out_2840849685208399580) {
   out_2840849685208399580[0] = delta_x[0] + nom_x[0];
   out_2840849685208399580[1] = delta_x[1] + nom_x[1];
   out_2840849685208399580[2] = delta_x[2] + nom_x[2];
   out_2840849685208399580[3] = delta_x[3] + nom_x[3];
   out_2840849685208399580[4] = delta_x[4] + nom_x[4];
   out_2840849685208399580[5] = delta_x[5] + nom_x[5];
   out_2840849685208399580[6] = delta_x[6] + nom_x[6];
   out_2840849685208399580[7] = delta_x[7] + nom_x[7];
   out_2840849685208399580[8] = delta_x[8] + nom_x[8];
   out_2840849685208399580[9] = delta_x[9] + nom_x[9];
   out_2840849685208399580[10] = delta_x[10] + nom_x[10];
   out_2840849685208399580[11] = delta_x[11] + nom_x[11];
   out_2840849685208399580[12] = delta_x[12] + nom_x[12];
   out_2840849685208399580[13] = delta_x[13] + nom_x[13];
   out_2840849685208399580[14] = delta_x[14] + nom_x[14];
   out_2840849685208399580[15] = delta_x[15] + nom_x[15];
   out_2840849685208399580[16] = delta_x[16] + nom_x[16];
   out_2840849685208399580[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2304315321105159078) {
   out_2304315321105159078[0] = -nom_x[0] + true_x[0];
   out_2304315321105159078[1] = -nom_x[1] + true_x[1];
   out_2304315321105159078[2] = -nom_x[2] + true_x[2];
   out_2304315321105159078[3] = -nom_x[3] + true_x[3];
   out_2304315321105159078[4] = -nom_x[4] + true_x[4];
   out_2304315321105159078[5] = -nom_x[5] + true_x[5];
   out_2304315321105159078[6] = -nom_x[6] + true_x[6];
   out_2304315321105159078[7] = -nom_x[7] + true_x[7];
   out_2304315321105159078[8] = -nom_x[8] + true_x[8];
   out_2304315321105159078[9] = -nom_x[9] + true_x[9];
   out_2304315321105159078[10] = -nom_x[10] + true_x[10];
   out_2304315321105159078[11] = -nom_x[11] + true_x[11];
   out_2304315321105159078[12] = -nom_x[12] + true_x[12];
   out_2304315321105159078[13] = -nom_x[13] + true_x[13];
   out_2304315321105159078[14] = -nom_x[14] + true_x[14];
   out_2304315321105159078[15] = -nom_x[15] + true_x[15];
   out_2304315321105159078[16] = -nom_x[16] + true_x[16];
   out_2304315321105159078[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8772695675045116403) {
   out_8772695675045116403[0] = 1.0;
   out_8772695675045116403[1] = 0.0;
   out_8772695675045116403[2] = 0.0;
   out_8772695675045116403[3] = 0.0;
   out_8772695675045116403[4] = 0.0;
   out_8772695675045116403[5] = 0.0;
   out_8772695675045116403[6] = 0.0;
   out_8772695675045116403[7] = 0.0;
   out_8772695675045116403[8] = 0.0;
   out_8772695675045116403[9] = 0.0;
   out_8772695675045116403[10] = 0.0;
   out_8772695675045116403[11] = 0.0;
   out_8772695675045116403[12] = 0.0;
   out_8772695675045116403[13] = 0.0;
   out_8772695675045116403[14] = 0.0;
   out_8772695675045116403[15] = 0.0;
   out_8772695675045116403[16] = 0.0;
   out_8772695675045116403[17] = 0.0;
   out_8772695675045116403[18] = 0.0;
   out_8772695675045116403[19] = 1.0;
   out_8772695675045116403[20] = 0.0;
   out_8772695675045116403[21] = 0.0;
   out_8772695675045116403[22] = 0.0;
   out_8772695675045116403[23] = 0.0;
   out_8772695675045116403[24] = 0.0;
   out_8772695675045116403[25] = 0.0;
   out_8772695675045116403[26] = 0.0;
   out_8772695675045116403[27] = 0.0;
   out_8772695675045116403[28] = 0.0;
   out_8772695675045116403[29] = 0.0;
   out_8772695675045116403[30] = 0.0;
   out_8772695675045116403[31] = 0.0;
   out_8772695675045116403[32] = 0.0;
   out_8772695675045116403[33] = 0.0;
   out_8772695675045116403[34] = 0.0;
   out_8772695675045116403[35] = 0.0;
   out_8772695675045116403[36] = 0.0;
   out_8772695675045116403[37] = 0.0;
   out_8772695675045116403[38] = 1.0;
   out_8772695675045116403[39] = 0.0;
   out_8772695675045116403[40] = 0.0;
   out_8772695675045116403[41] = 0.0;
   out_8772695675045116403[42] = 0.0;
   out_8772695675045116403[43] = 0.0;
   out_8772695675045116403[44] = 0.0;
   out_8772695675045116403[45] = 0.0;
   out_8772695675045116403[46] = 0.0;
   out_8772695675045116403[47] = 0.0;
   out_8772695675045116403[48] = 0.0;
   out_8772695675045116403[49] = 0.0;
   out_8772695675045116403[50] = 0.0;
   out_8772695675045116403[51] = 0.0;
   out_8772695675045116403[52] = 0.0;
   out_8772695675045116403[53] = 0.0;
   out_8772695675045116403[54] = 0.0;
   out_8772695675045116403[55] = 0.0;
   out_8772695675045116403[56] = 0.0;
   out_8772695675045116403[57] = 1.0;
   out_8772695675045116403[58] = 0.0;
   out_8772695675045116403[59] = 0.0;
   out_8772695675045116403[60] = 0.0;
   out_8772695675045116403[61] = 0.0;
   out_8772695675045116403[62] = 0.0;
   out_8772695675045116403[63] = 0.0;
   out_8772695675045116403[64] = 0.0;
   out_8772695675045116403[65] = 0.0;
   out_8772695675045116403[66] = 0.0;
   out_8772695675045116403[67] = 0.0;
   out_8772695675045116403[68] = 0.0;
   out_8772695675045116403[69] = 0.0;
   out_8772695675045116403[70] = 0.0;
   out_8772695675045116403[71] = 0.0;
   out_8772695675045116403[72] = 0.0;
   out_8772695675045116403[73] = 0.0;
   out_8772695675045116403[74] = 0.0;
   out_8772695675045116403[75] = 0.0;
   out_8772695675045116403[76] = 1.0;
   out_8772695675045116403[77] = 0.0;
   out_8772695675045116403[78] = 0.0;
   out_8772695675045116403[79] = 0.0;
   out_8772695675045116403[80] = 0.0;
   out_8772695675045116403[81] = 0.0;
   out_8772695675045116403[82] = 0.0;
   out_8772695675045116403[83] = 0.0;
   out_8772695675045116403[84] = 0.0;
   out_8772695675045116403[85] = 0.0;
   out_8772695675045116403[86] = 0.0;
   out_8772695675045116403[87] = 0.0;
   out_8772695675045116403[88] = 0.0;
   out_8772695675045116403[89] = 0.0;
   out_8772695675045116403[90] = 0.0;
   out_8772695675045116403[91] = 0.0;
   out_8772695675045116403[92] = 0.0;
   out_8772695675045116403[93] = 0.0;
   out_8772695675045116403[94] = 0.0;
   out_8772695675045116403[95] = 1.0;
   out_8772695675045116403[96] = 0.0;
   out_8772695675045116403[97] = 0.0;
   out_8772695675045116403[98] = 0.0;
   out_8772695675045116403[99] = 0.0;
   out_8772695675045116403[100] = 0.0;
   out_8772695675045116403[101] = 0.0;
   out_8772695675045116403[102] = 0.0;
   out_8772695675045116403[103] = 0.0;
   out_8772695675045116403[104] = 0.0;
   out_8772695675045116403[105] = 0.0;
   out_8772695675045116403[106] = 0.0;
   out_8772695675045116403[107] = 0.0;
   out_8772695675045116403[108] = 0.0;
   out_8772695675045116403[109] = 0.0;
   out_8772695675045116403[110] = 0.0;
   out_8772695675045116403[111] = 0.0;
   out_8772695675045116403[112] = 0.0;
   out_8772695675045116403[113] = 0.0;
   out_8772695675045116403[114] = 1.0;
   out_8772695675045116403[115] = 0.0;
   out_8772695675045116403[116] = 0.0;
   out_8772695675045116403[117] = 0.0;
   out_8772695675045116403[118] = 0.0;
   out_8772695675045116403[119] = 0.0;
   out_8772695675045116403[120] = 0.0;
   out_8772695675045116403[121] = 0.0;
   out_8772695675045116403[122] = 0.0;
   out_8772695675045116403[123] = 0.0;
   out_8772695675045116403[124] = 0.0;
   out_8772695675045116403[125] = 0.0;
   out_8772695675045116403[126] = 0.0;
   out_8772695675045116403[127] = 0.0;
   out_8772695675045116403[128] = 0.0;
   out_8772695675045116403[129] = 0.0;
   out_8772695675045116403[130] = 0.0;
   out_8772695675045116403[131] = 0.0;
   out_8772695675045116403[132] = 0.0;
   out_8772695675045116403[133] = 1.0;
   out_8772695675045116403[134] = 0.0;
   out_8772695675045116403[135] = 0.0;
   out_8772695675045116403[136] = 0.0;
   out_8772695675045116403[137] = 0.0;
   out_8772695675045116403[138] = 0.0;
   out_8772695675045116403[139] = 0.0;
   out_8772695675045116403[140] = 0.0;
   out_8772695675045116403[141] = 0.0;
   out_8772695675045116403[142] = 0.0;
   out_8772695675045116403[143] = 0.0;
   out_8772695675045116403[144] = 0.0;
   out_8772695675045116403[145] = 0.0;
   out_8772695675045116403[146] = 0.0;
   out_8772695675045116403[147] = 0.0;
   out_8772695675045116403[148] = 0.0;
   out_8772695675045116403[149] = 0.0;
   out_8772695675045116403[150] = 0.0;
   out_8772695675045116403[151] = 0.0;
   out_8772695675045116403[152] = 1.0;
   out_8772695675045116403[153] = 0.0;
   out_8772695675045116403[154] = 0.0;
   out_8772695675045116403[155] = 0.0;
   out_8772695675045116403[156] = 0.0;
   out_8772695675045116403[157] = 0.0;
   out_8772695675045116403[158] = 0.0;
   out_8772695675045116403[159] = 0.0;
   out_8772695675045116403[160] = 0.0;
   out_8772695675045116403[161] = 0.0;
   out_8772695675045116403[162] = 0.0;
   out_8772695675045116403[163] = 0.0;
   out_8772695675045116403[164] = 0.0;
   out_8772695675045116403[165] = 0.0;
   out_8772695675045116403[166] = 0.0;
   out_8772695675045116403[167] = 0.0;
   out_8772695675045116403[168] = 0.0;
   out_8772695675045116403[169] = 0.0;
   out_8772695675045116403[170] = 0.0;
   out_8772695675045116403[171] = 1.0;
   out_8772695675045116403[172] = 0.0;
   out_8772695675045116403[173] = 0.0;
   out_8772695675045116403[174] = 0.0;
   out_8772695675045116403[175] = 0.0;
   out_8772695675045116403[176] = 0.0;
   out_8772695675045116403[177] = 0.0;
   out_8772695675045116403[178] = 0.0;
   out_8772695675045116403[179] = 0.0;
   out_8772695675045116403[180] = 0.0;
   out_8772695675045116403[181] = 0.0;
   out_8772695675045116403[182] = 0.0;
   out_8772695675045116403[183] = 0.0;
   out_8772695675045116403[184] = 0.0;
   out_8772695675045116403[185] = 0.0;
   out_8772695675045116403[186] = 0.0;
   out_8772695675045116403[187] = 0.0;
   out_8772695675045116403[188] = 0.0;
   out_8772695675045116403[189] = 0.0;
   out_8772695675045116403[190] = 1.0;
   out_8772695675045116403[191] = 0.0;
   out_8772695675045116403[192] = 0.0;
   out_8772695675045116403[193] = 0.0;
   out_8772695675045116403[194] = 0.0;
   out_8772695675045116403[195] = 0.0;
   out_8772695675045116403[196] = 0.0;
   out_8772695675045116403[197] = 0.0;
   out_8772695675045116403[198] = 0.0;
   out_8772695675045116403[199] = 0.0;
   out_8772695675045116403[200] = 0.0;
   out_8772695675045116403[201] = 0.0;
   out_8772695675045116403[202] = 0.0;
   out_8772695675045116403[203] = 0.0;
   out_8772695675045116403[204] = 0.0;
   out_8772695675045116403[205] = 0.0;
   out_8772695675045116403[206] = 0.0;
   out_8772695675045116403[207] = 0.0;
   out_8772695675045116403[208] = 0.0;
   out_8772695675045116403[209] = 1.0;
   out_8772695675045116403[210] = 0.0;
   out_8772695675045116403[211] = 0.0;
   out_8772695675045116403[212] = 0.0;
   out_8772695675045116403[213] = 0.0;
   out_8772695675045116403[214] = 0.0;
   out_8772695675045116403[215] = 0.0;
   out_8772695675045116403[216] = 0.0;
   out_8772695675045116403[217] = 0.0;
   out_8772695675045116403[218] = 0.0;
   out_8772695675045116403[219] = 0.0;
   out_8772695675045116403[220] = 0.0;
   out_8772695675045116403[221] = 0.0;
   out_8772695675045116403[222] = 0.0;
   out_8772695675045116403[223] = 0.0;
   out_8772695675045116403[224] = 0.0;
   out_8772695675045116403[225] = 0.0;
   out_8772695675045116403[226] = 0.0;
   out_8772695675045116403[227] = 0.0;
   out_8772695675045116403[228] = 1.0;
   out_8772695675045116403[229] = 0.0;
   out_8772695675045116403[230] = 0.0;
   out_8772695675045116403[231] = 0.0;
   out_8772695675045116403[232] = 0.0;
   out_8772695675045116403[233] = 0.0;
   out_8772695675045116403[234] = 0.0;
   out_8772695675045116403[235] = 0.0;
   out_8772695675045116403[236] = 0.0;
   out_8772695675045116403[237] = 0.0;
   out_8772695675045116403[238] = 0.0;
   out_8772695675045116403[239] = 0.0;
   out_8772695675045116403[240] = 0.0;
   out_8772695675045116403[241] = 0.0;
   out_8772695675045116403[242] = 0.0;
   out_8772695675045116403[243] = 0.0;
   out_8772695675045116403[244] = 0.0;
   out_8772695675045116403[245] = 0.0;
   out_8772695675045116403[246] = 0.0;
   out_8772695675045116403[247] = 1.0;
   out_8772695675045116403[248] = 0.0;
   out_8772695675045116403[249] = 0.0;
   out_8772695675045116403[250] = 0.0;
   out_8772695675045116403[251] = 0.0;
   out_8772695675045116403[252] = 0.0;
   out_8772695675045116403[253] = 0.0;
   out_8772695675045116403[254] = 0.0;
   out_8772695675045116403[255] = 0.0;
   out_8772695675045116403[256] = 0.0;
   out_8772695675045116403[257] = 0.0;
   out_8772695675045116403[258] = 0.0;
   out_8772695675045116403[259] = 0.0;
   out_8772695675045116403[260] = 0.0;
   out_8772695675045116403[261] = 0.0;
   out_8772695675045116403[262] = 0.0;
   out_8772695675045116403[263] = 0.0;
   out_8772695675045116403[264] = 0.0;
   out_8772695675045116403[265] = 0.0;
   out_8772695675045116403[266] = 1.0;
   out_8772695675045116403[267] = 0.0;
   out_8772695675045116403[268] = 0.0;
   out_8772695675045116403[269] = 0.0;
   out_8772695675045116403[270] = 0.0;
   out_8772695675045116403[271] = 0.0;
   out_8772695675045116403[272] = 0.0;
   out_8772695675045116403[273] = 0.0;
   out_8772695675045116403[274] = 0.0;
   out_8772695675045116403[275] = 0.0;
   out_8772695675045116403[276] = 0.0;
   out_8772695675045116403[277] = 0.0;
   out_8772695675045116403[278] = 0.0;
   out_8772695675045116403[279] = 0.0;
   out_8772695675045116403[280] = 0.0;
   out_8772695675045116403[281] = 0.0;
   out_8772695675045116403[282] = 0.0;
   out_8772695675045116403[283] = 0.0;
   out_8772695675045116403[284] = 0.0;
   out_8772695675045116403[285] = 1.0;
   out_8772695675045116403[286] = 0.0;
   out_8772695675045116403[287] = 0.0;
   out_8772695675045116403[288] = 0.0;
   out_8772695675045116403[289] = 0.0;
   out_8772695675045116403[290] = 0.0;
   out_8772695675045116403[291] = 0.0;
   out_8772695675045116403[292] = 0.0;
   out_8772695675045116403[293] = 0.0;
   out_8772695675045116403[294] = 0.0;
   out_8772695675045116403[295] = 0.0;
   out_8772695675045116403[296] = 0.0;
   out_8772695675045116403[297] = 0.0;
   out_8772695675045116403[298] = 0.0;
   out_8772695675045116403[299] = 0.0;
   out_8772695675045116403[300] = 0.0;
   out_8772695675045116403[301] = 0.0;
   out_8772695675045116403[302] = 0.0;
   out_8772695675045116403[303] = 0.0;
   out_8772695675045116403[304] = 1.0;
   out_8772695675045116403[305] = 0.0;
   out_8772695675045116403[306] = 0.0;
   out_8772695675045116403[307] = 0.0;
   out_8772695675045116403[308] = 0.0;
   out_8772695675045116403[309] = 0.0;
   out_8772695675045116403[310] = 0.0;
   out_8772695675045116403[311] = 0.0;
   out_8772695675045116403[312] = 0.0;
   out_8772695675045116403[313] = 0.0;
   out_8772695675045116403[314] = 0.0;
   out_8772695675045116403[315] = 0.0;
   out_8772695675045116403[316] = 0.0;
   out_8772695675045116403[317] = 0.0;
   out_8772695675045116403[318] = 0.0;
   out_8772695675045116403[319] = 0.0;
   out_8772695675045116403[320] = 0.0;
   out_8772695675045116403[321] = 0.0;
   out_8772695675045116403[322] = 0.0;
   out_8772695675045116403[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8679165298156092092) {
   out_8679165298156092092[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8679165298156092092[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8679165298156092092[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8679165298156092092[3] = dt*state[12] + state[3];
   out_8679165298156092092[4] = dt*state[13] + state[4];
   out_8679165298156092092[5] = dt*state[14] + state[5];
   out_8679165298156092092[6] = state[6];
   out_8679165298156092092[7] = state[7];
   out_8679165298156092092[8] = state[8];
   out_8679165298156092092[9] = state[9];
   out_8679165298156092092[10] = state[10];
   out_8679165298156092092[11] = state[11];
   out_8679165298156092092[12] = state[12];
   out_8679165298156092092[13] = state[13];
   out_8679165298156092092[14] = state[14];
   out_8679165298156092092[15] = state[15];
   out_8679165298156092092[16] = state[16];
   out_8679165298156092092[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2287386913391151309) {
   out_2287386913391151309[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2287386913391151309[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2287386913391151309[2] = 0;
   out_2287386913391151309[3] = 0;
   out_2287386913391151309[4] = 0;
   out_2287386913391151309[5] = 0;
   out_2287386913391151309[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2287386913391151309[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2287386913391151309[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2287386913391151309[9] = 0;
   out_2287386913391151309[10] = 0;
   out_2287386913391151309[11] = 0;
   out_2287386913391151309[12] = 0;
   out_2287386913391151309[13] = 0;
   out_2287386913391151309[14] = 0;
   out_2287386913391151309[15] = 0;
   out_2287386913391151309[16] = 0;
   out_2287386913391151309[17] = 0;
   out_2287386913391151309[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2287386913391151309[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2287386913391151309[20] = 0;
   out_2287386913391151309[21] = 0;
   out_2287386913391151309[22] = 0;
   out_2287386913391151309[23] = 0;
   out_2287386913391151309[24] = 0;
   out_2287386913391151309[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2287386913391151309[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2287386913391151309[27] = 0;
   out_2287386913391151309[28] = 0;
   out_2287386913391151309[29] = 0;
   out_2287386913391151309[30] = 0;
   out_2287386913391151309[31] = 0;
   out_2287386913391151309[32] = 0;
   out_2287386913391151309[33] = 0;
   out_2287386913391151309[34] = 0;
   out_2287386913391151309[35] = 0;
   out_2287386913391151309[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2287386913391151309[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2287386913391151309[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2287386913391151309[39] = 0;
   out_2287386913391151309[40] = 0;
   out_2287386913391151309[41] = 0;
   out_2287386913391151309[42] = 0;
   out_2287386913391151309[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2287386913391151309[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2287386913391151309[45] = 0;
   out_2287386913391151309[46] = 0;
   out_2287386913391151309[47] = 0;
   out_2287386913391151309[48] = 0;
   out_2287386913391151309[49] = 0;
   out_2287386913391151309[50] = 0;
   out_2287386913391151309[51] = 0;
   out_2287386913391151309[52] = 0;
   out_2287386913391151309[53] = 0;
   out_2287386913391151309[54] = 0;
   out_2287386913391151309[55] = 0;
   out_2287386913391151309[56] = 0;
   out_2287386913391151309[57] = 1;
   out_2287386913391151309[58] = 0;
   out_2287386913391151309[59] = 0;
   out_2287386913391151309[60] = 0;
   out_2287386913391151309[61] = 0;
   out_2287386913391151309[62] = 0;
   out_2287386913391151309[63] = 0;
   out_2287386913391151309[64] = 0;
   out_2287386913391151309[65] = 0;
   out_2287386913391151309[66] = dt;
   out_2287386913391151309[67] = 0;
   out_2287386913391151309[68] = 0;
   out_2287386913391151309[69] = 0;
   out_2287386913391151309[70] = 0;
   out_2287386913391151309[71] = 0;
   out_2287386913391151309[72] = 0;
   out_2287386913391151309[73] = 0;
   out_2287386913391151309[74] = 0;
   out_2287386913391151309[75] = 0;
   out_2287386913391151309[76] = 1;
   out_2287386913391151309[77] = 0;
   out_2287386913391151309[78] = 0;
   out_2287386913391151309[79] = 0;
   out_2287386913391151309[80] = 0;
   out_2287386913391151309[81] = 0;
   out_2287386913391151309[82] = 0;
   out_2287386913391151309[83] = 0;
   out_2287386913391151309[84] = 0;
   out_2287386913391151309[85] = dt;
   out_2287386913391151309[86] = 0;
   out_2287386913391151309[87] = 0;
   out_2287386913391151309[88] = 0;
   out_2287386913391151309[89] = 0;
   out_2287386913391151309[90] = 0;
   out_2287386913391151309[91] = 0;
   out_2287386913391151309[92] = 0;
   out_2287386913391151309[93] = 0;
   out_2287386913391151309[94] = 0;
   out_2287386913391151309[95] = 1;
   out_2287386913391151309[96] = 0;
   out_2287386913391151309[97] = 0;
   out_2287386913391151309[98] = 0;
   out_2287386913391151309[99] = 0;
   out_2287386913391151309[100] = 0;
   out_2287386913391151309[101] = 0;
   out_2287386913391151309[102] = 0;
   out_2287386913391151309[103] = 0;
   out_2287386913391151309[104] = dt;
   out_2287386913391151309[105] = 0;
   out_2287386913391151309[106] = 0;
   out_2287386913391151309[107] = 0;
   out_2287386913391151309[108] = 0;
   out_2287386913391151309[109] = 0;
   out_2287386913391151309[110] = 0;
   out_2287386913391151309[111] = 0;
   out_2287386913391151309[112] = 0;
   out_2287386913391151309[113] = 0;
   out_2287386913391151309[114] = 1;
   out_2287386913391151309[115] = 0;
   out_2287386913391151309[116] = 0;
   out_2287386913391151309[117] = 0;
   out_2287386913391151309[118] = 0;
   out_2287386913391151309[119] = 0;
   out_2287386913391151309[120] = 0;
   out_2287386913391151309[121] = 0;
   out_2287386913391151309[122] = 0;
   out_2287386913391151309[123] = 0;
   out_2287386913391151309[124] = 0;
   out_2287386913391151309[125] = 0;
   out_2287386913391151309[126] = 0;
   out_2287386913391151309[127] = 0;
   out_2287386913391151309[128] = 0;
   out_2287386913391151309[129] = 0;
   out_2287386913391151309[130] = 0;
   out_2287386913391151309[131] = 0;
   out_2287386913391151309[132] = 0;
   out_2287386913391151309[133] = 1;
   out_2287386913391151309[134] = 0;
   out_2287386913391151309[135] = 0;
   out_2287386913391151309[136] = 0;
   out_2287386913391151309[137] = 0;
   out_2287386913391151309[138] = 0;
   out_2287386913391151309[139] = 0;
   out_2287386913391151309[140] = 0;
   out_2287386913391151309[141] = 0;
   out_2287386913391151309[142] = 0;
   out_2287386913391151309[143] = 0;
   out_2287386913391151309[144] = 0;
   out_2287386913391151309[145] = 0;
   out_2287386913391151309[146] = 0;
   out_2287386913391151309[147] = 0;
   out_2287386913391151309[148] = 0;
   out_2287386913391151309[149] = 0;
   out_2287386913391151309[150] = 0;
   out_2287386913391151309[151] = 0;
   out_2287386913391151309[152] = 1;
   out_2287386913391151309[153] = 0;
   out_2287386913391151309[154] = 0;
   out_2287386913391151309[155] = 0;
   out_2287386913391151309[156] = 0;
   out_2287386913391151309[157] = 0;
   out_2287386913391151309[158] = 0;
   out_2287386913391151309[159] = 0;
   out_2287386913391151309[160] = 0;
   out_2287386913391151309[161] = 0;
   out_2287386913391151309[162] = 0;
   out_2287386913391151309[163] = 0;
   out_2287386913391151309[164] = 0;
   out_2287386913391151309[165] = 0;
   out_2287386913391151309[166] = 0;
   out_2287386913391151309[167] = 0;
   out_2287386913391151309[168] = 0;
   out_2287386913391151309[169] = 0;
   out_2287386913391151309[170] = 0;
   out_2287386913391151309[171] = 1;
   out_2287386913391151309[172] = 0;
   out_2287386913391151309[173] = 0;
   out_2287386913391151309[174] = 0;
   out_2287386913391151309[175] = 0;
   out_2287386913391151309[176] = 0;
   out_2287386913391151309[177] = 0;
   out_2287386913391151309[178] = 0;
   out_2287386913391151309[179] = 0;
   out_2287386913391151309[180] = 0;
   out_2287386913391151309[181] = 0;
   out_2287386913391151309[182] = 0;
   out_2287386913391151309[183] = 0;
   out_2287386913391151309[184] = 0;
   out_2287386913391151309[185] = 0;
   out_2287386913391151309[186] = 0;
   out_2287386913391151309[187] = 0;
   out_2287386913391151309[188] = 0;
   out_2287386913391151309[189] = 0;
   out_2287386913391151309[190] = 1;
   out_2287386913391151309[191] = 0;
   out_2287386913391151309[192] = 0;
   out_2287386913391151309[193] = 0;
   out_2287386913391151309[194] = 0;
   out_2287386913391151309[195] = 0;
   out_2287386913391151309[196] = 0;
   out_2287386913391151309[197] = 0;
   out_2287386913391151309[198] = 0;
   out_2287386913391151309[199] = 0;
   out_2287386913391151309[200] = 0;
   out_2287386913391151309[201] = 0;
   out_2287386913391151309[202] = 0;
   out_2287386913391151309[203] = 0;
   out_2287386913391151309[204] = 0;
   out_2287386913391151309[205] = 0;
   out_2287386913391151309[206] = 0;
   out_2287386913391151309[207] = 0;
   out_2287386913391151309[208] = 0;
   out_2287386913391151309[209] = 1;
   out_2287386913391151309[210] = 0;
   out_2287386913391151309[211] = 0;
   out_2287386913391151309[212] = 0;
   out_2287386913391151309[213] = 0;
   out_2287386913391151309[214] = 0;
   out_2287386913391151309[215] = 0;
   out_2287386913391151309[216] = 0;
   out_2287386913391151309[217] = 0;
   out_2287386913391151309[218] = 0;
   out_2287386913391151309[219] = 0;
   out_2287386913391151309[220] = 0;
   out_2287386913391151309[221] = 0;
   out_2287386913391151309[222] = 0;
   out_2287386913391151309[223] = 0;
   out_2287386913391151309[224] = 0;
   out_2287386913391151309[225] = 0;
   out_2287386913391151309[226] = 0;
   out_2287386913391151309[227] = 0;
   out_2287386913391151309[228] = 1;
   out_2287386913391151309[229] = 0;
   out_2287386913391151309[230] = 0;
   out_2287386913391151309[231] = 0;
   out_2287386913391151309[232] = 0;
   out_2287386913391151309[233] = 0;
   out_2287386913391151309[234] = 0;
   out_2287386913391151309[235] = 0;
   out_2287386913391151309[236] = 0;
   out_2287386913391151309[237] = 0;
   out_2287386913391151309[238] = 0;
   out_2287386913391151309[239] = 0;
   out_2287386913391151309[240] = 0;
   out_2287386913391151309[241] = 0;
   out_2287386913391151309[242] = 0;
   out_2287386913391151309[243] = 0;
   out_2287386913391151309[244] = 0;
   out_2287386913391151309[245] = 0;
   out_2287386913391151309[246] = 0;
   out_2287386913391151309[247] = 1;
   out_2287386913391151309[248] = 0;
   out_2287386913391151309[249] = 0;
   out_2287386913391151309[250] = 0;
   out_2287386913391151309[251] = 0;
   out_2287386913391151309[252] = 0;
   out_2287386913391151309[253] = 0;
   out_2287386913391151309[254] = 0;
   out_2287386913391151309[255] = 0;
   out_2287386913391151309[256] = 0;
   out_2287386913391151309[257] = 0;
   out_2287386913391151309[258] = 0;
   out_2287386913391151309[259] = 0;
   out_2287386913391151309[260] = 0;
   out_2287386913391151309[261] = 0;
   out_2287386913391151309[262] = 0;
   out_2287386913391151309[263] = 0;
   out_2287386913391151309[264] = 0;
   out_2287386913391151309[265] = 0;
   out_2287386913391151309[266] = 1;
   out_2287386913391151309[267] = 0;
   out_2287386913391151309[268] = 0;
   out_2287386913391151309[269] = 0;
   out_2287386913391151309[270] = 0;
   out_2287386913391151309[271] = 0;
   out_2287386913391151309[272] = 0;
   out_2287386913391151309[273] = 0;
   out_2287386913391151309[274] = 0;
   out_2287386913391151309[275] = 0;
   out_2287386913391151309[276] = 0;
   out_2287386913391151309[277] = 0;
   out_2287386913391151309[278] = 0;
   out_2287386913391151309[279] = 0;
   out_2287386913391151309[280] = 0;
   out_2287386913391151309[281] = 0;
   out_2287386913391151309[282] = 0;
   out_2287386913391151309[283] = 0;
   out_2287386913391151309[284] = 0;
   out_2287386913391151309[285] = 1;
   out_2287386913391151309[286] = 0;
   out_2287386913391151309[287] = 0;
   out_2287386913391151309[288] = 0;
   out_2287386913391151309[289] = 0;
   out_2287386913391151309[290] = 0;
   out_2287386913391151309[291] = 0;
   out_2287386913391151309[292] = 0;
   out_2287386913391151309[293] = 0;
   out_2287386913391151309[294] = 0;
   out_2287386913391151309[295] = 0;
   out_2287386913391151309[296] = 0;
   out_2287386913391151309[297] = 0;
   out_2287386913391151309[298] = 0;
   out_2287386913391151309[299] = 0;
   out_2287386913391151309[300] = 0;
   out_2287386913391151309[301] = 0;
   out_2287386913391151309[302] = 0;
   out_2287386913391151309[303] = 0;
   out_2287386913391151309[304] = 1;
   out_2287386913391151309[305] = 0;
   out_2287386913391151309[306] = 0;
   out_2287386913391151309[307] = 0;
   out_2287386913391151309[308] = 0;
   out_2287386913391151309[309] = 0;
   out_2287386913391151309[310] = 0;
   out_2287386913391151309[311] = 0;
   out_2287386913391151309[312] = 0;
   out_2287386913391151309[313] = 0;
   out_2287386913391151309[314] = 0;
   out_2287386913391151309[315] = 0;
   out_2287386913391151309[316] = 0;
   out_2287386913391151309[317] = 0;
   out_2287386913391151309[318] = 0;
   out_2287386913391151309[319] = 0;
   out_2287386913391151309[320] = 0;
   out_2287386913391151309[321] = 0;
   out_2287386913391151309[322] = 0;
   out_2287386913391151309[323] = 1;
}
void h_4(double *state, double *unused, double *out_7225240582787038467) {
   out_7225240582787038467[0] = state[6] + state[9];
   out_7225240582787038467[1] = state[7] + state[10];
   out_7225240582787038467[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_729686732606613871) {
   out_729686732606613871[0] = 0;
   out_729686732606613871[1] = 0;
   out_729686732606613871[2] = 0;
   out_729686732606613871[3] = 0;
   out_729686732606613871[4] = 0;
   out_729686732606613871[5] = 0;
   out_729686732606613871[6] = 1;
   out_729686732606613871[7] = 0;
   out_729686732606613871[8] = 0;
   out_729686732606613871[9] = 1;
   out_729686732606613871[10] = 0;
   out_729686732606613871[11] = 0;
   out_729686732606613871[12] = 0;
   out_729686732606613871[13] = 0;
   out_729686732606613871[14] = 0;
   out_729686732606613871[15] = 0;
   out_729686732606613871[16] = 0;
   out_729686732606613871[17] = 0;
   out_729686732606613871[18] = 0;
   out_729686732606613871[19] = 0;
   out_729686732606613871[20] = 0;
   out_729686732606613871[21] = 0;
   out_729686732606613871[22] = 0;
   out_729686732606613871[23] = 0;
   out_729686732606613871[24] = 0;
   out_729686732606613871[25] = 1;
   out_729686732606613871[26] = 0;
   out_729686732606613871[27] = 0;
   out_729686732606613871[28] = 1;
   out_729686732606613871[29] = 0;
   out_729686732606613871[30] = 0;
   out_729686732606613871[31] = 0;
   out_729686732606613871[32] = 0;
   out_729686732606613871[33] = 0;
   out_729686732606613871[34] = 0;
   out_729686732606613871[35] = 0;
   out_729686732606613871[36] = 0;
   out_729686732606613871[37] = 0;
   out_729686732606613871[38] = 0;
   out_729686732606613871[39] = 0;
   out_729686732606613871[40] = 0;
   out_729686732606613871[41] = 0;
   out_729686732606613871[42] = 0;
   out_729686732606613871[43] = 0;
   out_729686732606613871[44] = 1;
   out_729686732606613871[45] = 0;
   out_729686732606613871[46] = 0;
   out_729686732606613871[47] = 1;
   out_729686732606613871[48] = 0;
   out_729686732606613871[49] = 0;
   out_729686732606613871[50] = 0;
   out_729686732606613871[51] = 0;
   out_729686732606613871[52] = 0;
   out_729686732606613871[53] = 0;
}
void h_10(double *state, double *unused, double *out_6771917199724722492) {
   out_6771917199724722492[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6771917199724722492[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6771917199724722492[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_1701889044214050319) {
   out_1701889044214050319[0] = 0;
   out_1701889044214050319[1] = 9.8100000000000005*cos(state[1]);
   out_1701889044214050319[2] = 0;
   out_1701889044214050319[3] = 0;
   out_1701889044214050319[4] = -state[8];
   out_1701889044214050319[5] = state[7];
   out_1701889044214050319[6] = 0;
   out_1701889044214050319[7] = state[5];
   out_1701889044214050319[8] = -state[4];
   out_1701889044214050319[9] = 0;
   out_1701889044214050319[10] = 0;
   out_1701889044214050319[11] = 0;
   out_1701889044214050319[12] = 1;
   out_1701889044214050319[13] = 0;
   out_1701889044214050319[14] = 0;
   out_1701889044214050319[15] = 1;
   out_1701889044214050319[16] = 0;
   out_1701889044214050319[17] = 0;
   out_1701889044214050319[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_1701889044214050319[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_1701889044214050319[20] = 0;
   out_1701889044214050319[21] = state[8];
   out_1701889044214050319[22] = 0;
   out_1701889044214050319[23] = -state[6];
   out_1701889044214050319[24] = -state[5];
   out_1701889044214050319[25] = 0;
   out_1701889044214050319[26] = state[3];
   out_1701889044214050319[27] = 0;
   out_1701889044214050319[28] = 0;
   out_1701889044214050319[29] = 0;
   out_1701889044214050319[30] = 0;
   out_1701889044214050319[31] = 1;
   out_1701889044214050319[32] = 0;
   out_1701889044214050319[33] = 0;
   out_1701889044214050319[34] = 1;
   out_1701889044214050319[35] = 0;
   out_1701889044214050319[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_1701889044214050319[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_1701889044214050319[38] = 0;
   out_1701889044214050319[39] = -state[7];
   out_1701889044214050319[40] = state[6];
   out_1701889044214050319[41] = 0;
   out_1701889044214050319[42] = state[4];
   out_1701889044214050319[43] = -state[3];
   out_1701889044214050319[44] = 0;
   out_1701889044214050319[45] = 0;
   out_1701889044214050319[46] = 0;
   out_1701889044214050319[47] = 0;
   out_1701889044214050319[48] = 0;
   out_1701889044214050319[49] = 0;
   out_1701889044214050319[50] = 1;
   out_1701889044214050319[51] = 0;
   out_1701889044214050319[52] = 0;
   out_1701889044214050319[53] = 1;
}
void h_13(double *state, double *unused, double *out_348279363800690429) {
   out_348279363800690429[0] = state[3];
   out_348279363800690429[1] = state[4];
   out_348279363800690429[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3941960557938946672) {
   out_3941960557938946672[0] = 0;
   out_3941960557938946672[1] = 0;
   out_3941960557938946672[2] = 0;
   out_3941960557938946672[3] = 1;
   out_3941960557938946672[4] = 0;
   out_3941960557938946672[5] = 0;
   out_3941960557938946672[6] = 0;
   out_3941960557938946672[7] = 0;
   out_3941960557938946672[8] = 0;
   out_3941960557938946672[9] = 0;
   out_3941960557938946672[10] = 0;
   out_3941960557938946672[11] = 0;
   out_3941960557938946672[12] = 0;
   out_3941960557938946672[13] = 0;
   out_3941960557938946672[14] = 0;
   out_3941960557938946672[15] = 0;
   out_3941960557938946672[16] = 0;
   out_3941960557938946672[17] = 0;
   out_3941960557938946672[18] = 0;
   out_3941960557938946672[19] = 0;
   out_3941960557938946672[20] = 0;
   out_3941960557938946672[21] = 0;
   out_3941960557938946672[22] = 1;
   out_3941960557938946672[23] = 0;
   out_3941960557938946672[24] = 0;
   out_3941960557938946672[25] = 0;
   out_3941960557938946672[26] = 0;
   out_3941960557938946672[27] = 0;
   out_3941960557938946672[28] = 0;
   out_3941960557938946672[29] = 0;
   out_3941960557938946672[30] = 0;
   out_3941960557938946672[31] = 0;
   out_3941960557938946672[32] = 0;
   out_3941960557938946672[33] = 0;
   out_3941960557938946672[34] = 0;
   out_3941960557938946672[35] = 0;
   out_3941960557938946672[36] = 0;
   out_3941960557938946672[37] = 0;
   out_3941960557938946672[38] = 0;
   out_3941960557938946672[39] = 0;
   out_3941960557938946672[40] = 0;
   out_3941960557938946672[41] = 1;
   out_3941960557938946672[42] = 0;
   out_3941960557938946672[43] = 0;
   out_3941960557938946672[44] = 0;
   out_3941960557938946672[45] = 0;
   out_3941960557938946672[46] = 0;
   out_3941960557938946672[47] = 0;
   out_3941960557938946672[48] = 0;
   out_3941960557938946672[49] = 0;
   out_3941960557938946672[50] = 0;
   out_3941960557938946672[51] = 0;
   out_3941960557938946672[52] = 0;
   out_3941960557938946672[53] = 0;
}
void h_14(double *state, double *unused, double *out_7323634935456606723) {
   out_7323634935456606723[0] = state[6];
   out_7323634935456606723[1] = state[7];
   out_7323634935456606723[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4692927588946098400) {
   out_4692927588946098400[0] = 0;
   out_4692927588946098400[1] = 0;
   out_4692927588946098400[2] = 0;
   out_4692927588946098400[3] = 0;
   out_4692927588946098400[4] = 0;
   out_4692927588946098400[5] = 0;
   out_4692927588946098400[6] = 1;
   out_4692927588946098400[7] = 0;
   out_4692927588946098400[8] = 0;
   out_4692927588946098400[9] = 0;
   out_4692927588946098400[10] = 0;
   out_4692927588946098400[11] = 0;
   out_4692927588946098400[12] = 0;
   out_4692927588946098400[13] = 0;
   out_4692927588946098400[14] = 0;
   out_4692927588946098400[15] = 0;
   out_4692927588946098400[16] = 0;
   out_4692927588946098400[17] = 0;
   out_4692927588946098400[18] = 0;
   out_4692927588946098400[19] = 0;
   out_4692927588946098400[20] = 0;
   out_4692927588946098400[21] = 0;
   out_4692927588946098400[22] = 0;
   out_4692927588946098400[23] = 0;
   out_4692927588946098400[24] = 0;
   out_4692927588946098400[25] = 1;
   out_4692927588946098400[26] = 0;
   out_4692927588946098400[27] = 0;
   out_4692927588946098400[28] = 0;
   out_4692927588946098400[29] = 0;
   out_4692927588946098400[30] = 0;
   out_4692927588946098400[31] = 0;
   out_4692927588946098400[32] = 0;
   out_4692927588946098400[33] = 0;
   out_4692927588946098400[34] = 0;
   out_4692927588946098400[35] = 0;
   out_4692927588946098400[36] = 0;
   out_4692927588946098400[37] = 0;
   out_4692927588946098400[38] = 0;
   out_4692927588946098400[39] = 0;
   out_4692927588946098400[40] = 0;
   out_4692927588946098400[41] = 0;
   out_4692927588946098400[42] = 0;
   out_4692927588946098400[43] = 0;
   out_4692927588946098400[44] = 1;
   out_4692927588946098400[45] = 0;
   out_4692927588946098400[46] = 0;
   out_4692927588946098400[47] = 0;
   out_4692927588946098400[48] = 0;
   out_4692927588946098400[49] = 0;
   out_4692927588946098400[50] = 0;
   out_4692927588946098400[51] = 0;
   out_4692927588946098400[52] = 0;
   out_4692927588946098400[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_2840849685208399580) {
  err_fun(nom_x, delta_x, out_2840849685208399580);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2304315321105159078) {
  inv_err_fun(nom_x, true_x, out_2304315321105159078);
}
void pose_H_mod_fun(double *state, double *out_8772695675045116403) {
  H_mod_fun(state, out_8772695675045116403);
}
void pose_f_fun(double *state, double dt, double *out_8679165298156092092) {
  f_fun(state,  dt, out_8679165298156092092);
}
void pose_F_fun(double *state, double dt, double *out_2287386913391151309) {
  F_fun(state,  dt, out_2287386913391151309);
}
void pose_h_4(double *state, double *unused, double *out_7225240582787038467) {
  h_4(state, unused, out_7225240582787038467);
}
void pose_H_4(double *state, double *unused, double *out_729686732606613871) {
  H_4(state, unused, out_729686732606613871);
}
void pose_h_10(double *state, double *unused, double *out_6771917199724722492) {
  h_10(state, unused, out_6771917199724722492);
}
void pose_H_10(double *state, double *unused, double *out_1701889044214050319) {
  H_10(state, unused, out_1701889044214050319);
}
void pose_h_13(double *state, double *unused, double *out_348279363800690429) {
  h_13(state, unused, out_348279363800690429);
}
void pose_H_13(double *state, double *unused, double *out_3941960557938946672) {
  H_13(state, unused, out_3941960557938946672);
}
void pose_h_14(double *state, double *unused, double *out_7323634935456606723) {
  h_14(state, unused, out_7323634935456606723);
}
void pose_H_14(double *state, double *unused, double *out_4692927588946098400) {
  H_14(state, unused, out_4692927588946098400);
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
