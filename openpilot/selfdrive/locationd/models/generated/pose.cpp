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
void err_fun(double *nom_x, double *delta_x, double *out_4299274199831556809) {
   out_4299274199831556809[0] = delta_x[0] + nom_x[0];
   out_4299274199831556809[1] = delta_x[1] + nom_x[1];
   out_4299274199831556809[2] = delta_x[2] + nom_x[2];
   out_4299274199831556809[3] = delta_x[3] + nom_x[3];
   out_4299274199831556809[4] = delta_x[4] + nom_x[4];
   out_4299274199831556809[5] = delta_x[5] + nom_x[5];
   out_4299274199831556809[6] = delta_x[6] + nom_x[6];
   out_4299274199831556809[7] = delta_x[7] + nom_x[7];
   out_4299274199831556809[8] = delta_x[8] + nom_x[8];
   out_4299274199831556809[9] = delta_x[9] + nom_x[9];
   out_4299274199831556809[10] = delta_x[10] + nom_x[10];
   out_4299274199831556809[11] = delta_x[11] + nom_x[11];
   out_4299274199831556809[12] = delta_x[12] + nom_x[12];
   out_4299274199831556809[13] = delta_x[13] + nom_x[13];
   out_4299274199831556809[14] = delta_x[14] + nom_x[14];
   out_4299274199831556809[15] = delta_x[15] + nom_x[15];
   out_4299274199831556809[16] = delta_x[16] + nom_x[16];
   out_4299274199831556809[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2345037795202932384) {
   out_2345037795202932384[0] = -nom_x[0] + true_x[0];
   out_2345037795202932384[1] = -nom_x[1] + true_x[1];
   out_2345037795202932384[2] = -nom_x[2] + true_x[2];
   out_2345037795202932384[3] = -nom_x[3] + true_x[3];
   out_2345037795202932384[4] = -nom_x[4] + true_x[4];
   out_2345037795202932384[5] = -nom_x[5] + true_x[5];
   out_2345037795202932384[6] = -nom_x[6] + true_x[6];
   out_2345037795202932384[7] = -nom_x[7] + true_x[7];
   out_2345037795202932384[8] = -nom_x[8] + true_x[8];
   out_2345037795202932384[9] = -nom_x[9] + true_x[9];
   out_2345037795202932384[10] = -nom_x[10] + true_x[10];
   out_2345037795202932384[11] = -nom_x[11] + true_x[11];
   out_2345037795202932384[12] = -nom_x[12] + true_x[12];
   out_2345037795202932384[13] = -nom_x[13] + true_x[13];
   out_2345037795202932384[14] = -nom_x[14] + true_x[14];
   out_2345037795202932384[15] = -nom_x[15] + true_x[15];
   out_2345037795202932384[16] = -nom_x[16] + true_x[16];
   out_2345037795202932384[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2098398821367927813) {
   out_2098398821367927813[0] = 1.0;
   out_2098398821367927813[1] = 0.0;
   out_2098398821367927813[2] = 0.0;
   out_2098398821367927813[3] = 0.0;
   out_2098398821367927813[4] = 0.0;
   out_2098398821367927813[5] = 0.0;
   out_2098398821367927813[6] = 0.0;
   out_2098398821367927813[7] = 0.0;
   out_2098398821367927813[8] = 0.0;
   out_2098398821367927813[9] = 0.0;
   out_2098398821367927813[10] = 0.0;
   out_2098398821367927813[11] = 0.0;
   out_2098398821367927813[12] = 0.0;
   out_2098398821367927813[13] = 0.0;
   out_2098398821367927813[14] = 0.0;
   out_2098398821367927813[15] = 0.0;
   out_2098398821367927813[16] = 0.0;
   out_2098398821367927813[17] = 0.0;
   out_2098398821367927813[18] = 0.0;
   out_2098398821367927813[19] = 1.0;
   out_2098398821367927813[20] = 0.0;
   out_2098398821367927813[21] = 0.0;
   out_2098398821367927813[22] = 0.0;
   out_2098398821367927813[23] = 0.0;
   out_2098398821367927813[24] = 0.0;
   out_2098398821367927813[25] = 0.0;
   out_2098398821367927813[26] = 0.0;
   out_2098398821367927813[27] = 0.0;
   out_2098398821367927813[28] = 0.0;
   out_2098398821367927813[29] = 0.0;
   out_2098398821367927813[30] = 0.0;
   out_2098398821367927813[31] = 0.0;
   out_2098398821367927813[32] = 0.0;
   out_2098398821367927813[33] = 0.0;
   out_2098398821367927813[34] = 0.0;
   out_2098398821367927813[35] = 0.0;
   out_2098398821367927813[36] = 0.0;
   out_2098398821367927813[37] = 0.0;
   out_2098398821367927813[38] = 1.0;
   out_2098398821367927813[39] = 0.0;
   out_2098398821367927813[40] = 0.0;
   out_2098398821367927813[41] = 0.0;
   out_2098398821367927813[42] = 0.0;
   out_2098398821367927813[43] = 0.0;
   out_2098398821367927813[44] = 0.0;
   out_2098398821367927813[45] = 0.0;
   out_2098398821367927813[46] = 0.0;
   out_2098398821367927813[47] = 0.0;
   out_2098398821367927813[48] = 0.0;
   out_2098398821367927813[49] = 0.0;
   out_2098398821367927813[50] = 0.0;
   out_2098398821367927813[51] = 0.0;
   out_2098398821367927813[52] = 0.0;
   out_2098398821367927813[53] = 0.0;
   out_2098398821367927813[54] = 0.0;
   out_2098398821367927813[55] = 0.0;
   out_2098398821367927813[56] = 0.0;
   out_2098398821367927813[57] = 1.0;
   out_2098398821367927813[58] = 0.0;
   out_2098398821367927813[59] = 0.0;
   out_2098398821367927813[60] = 0.0;
   out_2098398821367927813[61] = 0.0;
   out_2098398821367927813[62] = 0.0;
   out_2098398821367927813[63] = 0.0;
   out_2098398821367927813[64] = 0.0;
   out_2098398821367927813[65] = 0.0;
   out_2098398821367927813[66] = 0.0;
   out_2098398821367927813[67] = 0.0;
   out_2098398821367927813[68] = 0.0;
   out_2098398821367927813[69] = 0.0;
   out_2098398821367927813[70] = 0.0;
   out_2098398821367927813[71] = 0.0;
   out_2098398821367927813[72] = 0.0;
   out_2098398821367927813[73] = 0.0;
   out_2098398821367927813[74] = 0.0;
   out_2098398821367927813[75] = 0.0;
   out_2098398821367927813[76] = 1.0;
   out_2098398821367927813[77] = 0.0;
   out_2098398821367927813[78] = 0.0;
   out_2098398821367927813[79] = 0.0;
   out_2098398821367927813[80] = 0.0;
   out_2098398821367927813[81] = 0.0;
   out_2098398821367927813[82] = 0.0;
   out_2098398821367927813[83] = 0.0;
   out_2098398821367927813[84] = 0.0;
   out_2098398821367927813[85] = 0.0;
   out_2098398821367927813[86] = 0.0;
   out_2098398821367927813[87] = 0.0;
   out_2098398821367927813[88] = 0.0;
   out_2098398821367927813[89] = 0.0;
   out_2098398821367927813[90] = 0.0;
   out_2098398821367927813[91] = 0.0;
   out_2098398821367927813[92] = 0.0;
   out_2098398821367927813[93] = 0.0;
   out_2098398821367927813[94] = 0.0;
   out_2098398821367927813[95] = 1.0;
   out_2098398821367927813[96] = 0.0;
   out_2098398821367927813[97] = 0.0;
   out_2098398821367927813[98] = 0.0;
   out_2098398821367927813[99] = 0.0;
   out_2098398821367927813[100] = 0.0;
   out_2098398821367927813[101] = 0.0;
   out_2098398821367927813[102] = 0.0;
   out_2098398821367927813[103] = 0.0;
   out_2098398821367927813[104] = 0.0;
   out_2098398821367927813[105] = 0.0;
   out_2098398821367927813[106] = 0.0;
   out_2098398821367927813[107] = 0.0;
   out_2098398821367927813[108] = 0.0;
   out_2098398821367927813[109] = 0.0;
   out_2098398821367927813[110] = 0.0;
   out_2098398821367927813[111] = 0.0;
   out_2098398821367927813[112] = 0.0;
   out_2098398821367927813[113] = 0.0;
   out_2098398821367927813[114] = 1.0;
   out_2098398821367927813[115] = 0.0;
   out_2098398821367927813[116] = 0.0;
   out_2098398821367927813[117] = 0.0;
   out_2098398821367927813[118] = 0.0;
   out_2098398821367927813[119] = 0.0;
   out_2098398821367927813[120] = 0.0;
   out_2098398821367927813[121] = 0.0;
   out_2098398821367927813[122] = 0.0;
   out_2098398821367927813[123] = 0.0;
   out_2098398821367927813[124] = 0.0;
   out_2098398821367927813[125] = 0.0;
   out_2098398821367927813[126] = 0.0;
   out_2098398821367927813[127] = 0.0;
   out_2098398821367927813[128] = 0.0;
   out_2098398821367927813[129] = 0.0;
   out_2098398821367927813[130] = 0.0;
   out_2098398821367927813[131] = 0.0;
   out_2098398821367927813[132] = 0.0;
   out_2098398821367927813[133] = 1.0;
   out_2098398821367927813[134] = 0.0;
   out_2098398821367927813[135] = 0.0;
   out_2098398821367927813[136] = 0.0;
   out_2098398821367927813[137] = 0.0;
   out_2098398821367927813[138] = 0.0;
   out_2098398821367927813[139] = 0.0;
   out_2098398821367927813[140] = 0.0;
   out_2098398821367927813[141] = 0.0;
   out_2098398821367927813[142] = 0.0;
   out_2098398821367927813[143] = 0.0;
   out_2098398821367927813[144] = 0.0;
   out_2098398821367927813[145] = 0.0;
   out_2098398821367927813[146] = 0.0;
   out_2098398821367927813[147] = 0.0;
   out_2098398821367927813[148] = 0.0;
   out_2098398821367927813[149] = 0.0;
   out_2098398821367927813[150] = 0.0;
   out_2098398821367927813[151] = 0.0;
   out_2098398821367927813[152] = 1.0;
   out_2098398821367927813[153] = 0.0;
   out_2098398821367927813[154] = 0.0;
   out_2098398821367927813[155] = 0.0;
   out_2098398821367927813[156] = 0.0;
   out_2098398821367927813[157] = 0.0;
   out_2098398821367927813[158] = 0.0;
   out_2098398821367927813[159] = 0.0;
   out_2098398821367927813[160] = 0.0;
   out_2098398821367927813[161] = 0.0;
   out_2098398821367927813[162] = 0.0;
   out_2098398821367927813[163] = 0.0;
   out_2098398821367927813[164] = 0.0;
   out_2098398821367927813[165] = 0.0;
   out_2098398821367927813[166] = 0.0;
   out_2098398821367927813[167] = 0.0;
   out_2098398821367927813[168] = 0.0;
   out_2098398821367927813[169] = 0.0;
   out_2098398821367927813[170] = 0.0;
   out_2098398821367927813[171] = 1.0;
   out_2098398821367927813[172] = 0.0;
   out_2098398821367927813[173] = 0.0;
   out_2098398821367927813[174] = 0.0;
   out_2098398821367927813[175] = 0.0;
   out_2098398821367927813[176] = 0.0;
   out_2098398821367927813[177] = 0.0;
   out_2098398821367927813[178] = 0.0;
   out_2098398821367927813[179] = 0.0;
   out_2098398821367927813[180] = 0.0;
   out_2098398821367927813[181] = 0.0;
   out_2098398821367927813[182] = 0.0;
   out_2098398821367927813[183] = 0.0;
   out_2098398821367927813[184] = 0.0;
   out_2098398821367927813[185] = 0.0;
   out_2098398821367927813[186] = 0.0;
   out_2098398821367927813[187] = 0.0;
   out_2098398821367927813[188] = 0.0;
   out_2098398821367927813[189] = 0.0;
   out_2098398821367927813[190] = 1.0;
   out_2098398821367927813[191] = 0.0;
   out_2098398821367927813[192] = 0.0;
   out_2098398821367927813[193] = 0.0;
   out_2098398821367927813[194] = 0.0;
   out_2098398821367927813[195] = 0.0;
   out_2098398821367927813[196] = 0.0;
   out_2098398821367927813[197] = 0.0;
   out_2098398821367927813[198] = 0.0;
   out_2098398821367927813[199] = 0.0;
   out_2098398821367927813[200] = 0.0;
   out_2098398821367927813[201] = 0.0;
   out_2098398821367927813[202] = 0.0;
   out_2098398821367927813[203] = 0.0;
   out_2098398821367927813[204] = 0.0;
   out_2098398821367927813[205] = 0.0;
   out_2098398821367927813[206] = 0.0;
   out_2098398821367927813[207] = 0.0;
   out_2098398821367927813[208] = 0.0;
   out_2098398821367927813[209] = 1.0;
   out_2098398821367927813[210] = 0.0;
   out_2098398821367927813[211] = 0.0;
   out_2098398821367927813[212] = 0.0;
   out_2098398821367927813[213] = 0.0;
   out_2098398821367927813[214] = 0.0;
   out_2098398821367927813[215] = 0.0;
   out_2098398821367927813[216] = 0.0;
   out_2098398821367927813[217] = 0.0;
   out_2098398821367927813[218] = 0.0;
   out_2098398821367927813[219] = 0.0;
   out_2098398821367927813[220] = 0.0;
   out_2098398821367927813[221] = 0.0;
   out_2098398821367927813[222] = 0.0;
   out_2098398821367927813[223] = 0.0;
   out_2098398821367927813[224] = 0.0;
   out_2098398821367927813[225] = 0.0;
   out_2098398821367927813[226] = 0.0;
   out_2098398821367927813[227] = 0.0;
   out_2098398821367927813[228] = 1.0;
   out_2098398821367927813[229] = 0.0;
   out_2098398821367927813[230] = 0.0;
   out_2098398821367927813[231] = 0.0;
   out_2098398821367927813[232] = 0.0;
   out_2098398821367927813[233] = 0.0;
   out_2098398821367927813[234] = 0.0;
   out_2098398821367927813[235] = 0.0;
   out_2098398821367927813[236] = 0.0;
   out_2098398821367927813[237] = 0.0;
   out_2098398821367927813[238] = 0.0;
   out_2098398821367927813[239] = 0.0;
   out_2098398821367927813[240] = 0.0;
   out_2098398821367927813[241] = 0.0;
   out_2098398821367927813[242] = 0.0;
   out_2098398821367927813[243] = 0.0;
   out_2098398821367927813[244] = 0.0;
   out_2098398821367927813[245] = 0.0;
   out_2098398821367927813[246] = 0.0;
   out_2098398821367927813[247] = 1.0;
   out_2098398821367927813[248] = 0.0;
   out_2098398821367927813[249] = 0.0;
   out_2098398821367927813[250] = 0.0;
   out_2098398821367927813[251] = 0.0;
   out_2098398821367927813[252] = 0.0;
   out_2098398821367927813[253] = 0.0;
   out_2098398821367927813[254] = 0.0;
   out_2098398821367927813[255] = 0.0;
   out_2098398821367927813[256] = 0.0;
   out_2098398821367927813[257] = 0.0;
   out_2098398821367927813[258] = 0.0;
   out_2098398821367927813[259] = 0.0;
   out_2098398821367927813[260] = 0.0;
   out_2098398821367927813[261] = 0.0;
   out_2098398821367927813[262] = 0.0;
   out_2098398821367927813[263] = 0.0;
   out_2098398821367927813[264] = 0.0;
   out_2098398821367927813[265] = 0.0;
   out_2098398821367927813[266] = 1.0;
   out_2098398821367927813[267] = 0.0;
   out_2098398821367927813[268] = 0.0;
   out_2098398821367927813[269] = 0.0;
   out_2098398821367927813[270] = 0.0;
   out_2098398821367927813[271] = 0.0;
   out_2098398821367927813[272] = 0.0;
   out_2098398821367927813[273] = 0.0;
   out_2098398821367927813[274] = 0.0;
   out_2098398821367927813[275] = 0.0;
   out_2098398821367927813[276] = 0.0;
   out_2098398821367927813[277] = 0.0;
   out_2098398821367927813[278] = 0.0;
   out_2098398821367927813[279] = 0.0;
   out_2098398821367927813[280] = 0.0;
   out_2098398821367927813[281] = 0.0;
   out_2098398821367927813[282] = 0.0;
   out_2098398821367927813[283] = 0.0;
   out_2098398821367927813[284] = 0.0;
   out_2098398821367927813[285] = 1.0;
   out_2098398821367927813[286] = 0.0;
   out_2098398821367927813[287] = 0.0;
   out_2098398821367927813[288] = 0.0;
   out_2098398821367927813[289] = 0.0;
   out_2098398821367927813[290] = 0.0;
   out_2098398821367927813[291] = 0.0;
   out_2098398821367927813[292] = 0.0;
   out_2098398821367927813[293] = 0.0;
   out_2098398821367927813[294] = 0.0;
   out_2098398821367927813[295] = 0.0;
   out_2098398821367927813[296] = 0.0;
   out_2098398821367927813[297] = 0.0;
   out_2098398821367927813[298] = 0.0;
   out_2098398821367927813[299] = 0.0;
   out_2098398821367927813[300] = 0.0;
   out_2098398821367927813[301] = 0.0;
   out_2098398821367927813[302] = 0.0;
   out_2098398821367927813[303] = 0.0;
   out_2098398821367927813[304] = 1.0;
   out_2098398821367927813[305] = 0.0;
   out_2098398821367927813[306] = 0.0;
   out_2098398821367927813[307] = 0.0;
   out_2098398821367927813[308] = 0.0;
   out_2098398821367927813[309] = 0.0;
   out_2098398821367927813[310] = 0.0;
   out_2098398821367927813[311] = 0.0;
   out_2098398821367927813[312] = 0.0;
   out_2098398821367927813[313] = 0.0;
   out_2098398821367927813[314] = 0.0;
   out_2098398821367927813[315] = 0.0;
   out_2098398821367927813[316] = 0.0;
   out_2098398821367927813[317] = 0.0;
   out_2098398821367927813[318] = 0.0;
   out_2098398821367927813[319] = 0.0;
   out_2098398821367927813[320] = 0.0;
   out_2098398821367927813[321] = 0.0;
   out_2098398821367927813[322] = 0.0;
   out_2098398821367927813[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5430492952832692036) {
   out_5430492952832692036[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5430492952832692036[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5430492952832692036[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5430492952832692036[3] = dt*state[12] + state[3];
   out_5430492952832692036[4] = dt*state[13] + state[4];
   out_5430492952832692036[5] = dt*state[14] + state[5];
   out_5430492952832692036[6] = state[6];
   out_5430492952832692036[7] = state[7];
   out_5430492952832692036[8] = state[8];
   out_5430492952832692036[9] = state[9];
   out_5430492952832692036[10] = state[10];
   out_5430492952832692036[11] = state[11];
   out_5430492952832692036[12] = state[12];
   out_5430492952832692036[13] = state[13];
   out_5430492952832692036[14] = state[14];
   out_5430492952832692036[15] = state[15];
   out_5430492952832692036[16] = state[16];
   out_5430492952832692036[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8675558556930303753) {
   out_8675558556930303753[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8675558556930303753[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8675558556930303753[2] = 0;
   out_8675558556930303753[3] = 0;
   out_8675558556930303753[4] = 0;
   out_8675558556930303753[5] = 0;
   out_8675558556930303753[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8675558556930303753[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8675558556930303753[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8675558556930303753[9] = 0;
   out_8675558556930303753[10] = 0;
   out_8675558556930303753[11] = 0;
   out_8675558556930303753[12] = 0;
   out_8675558556930303753[13] = 0;
   out_8675558556930303753[14] = 0;
   out_8675558556930303753[15] = 0;
   out_8675558556930303753[16] = 0;
   out_8675558556930303753[17] = 0;
   out_8675558556930303753[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8675558556930303753[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8675558556930303753[20] = 0;
   out_8675558556930303753[21] = 0;
   out_8675558556930303753[22] = 0;
   out_8675558556930303753[23] = 0;
   out_8675558556930303753[24] = 0;
   out_8675558556930303753[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8675558556930303753[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8675558556930303753[27] = 0;
   out_8675558556930303753[28] = 0;
   out_8675558556930303753[29] = 0;
   out_8675558556930303753[30] = 0;
   out_8675558556930303753[31] = 0;
   out_8675558556930303753[32] = 0;
   out_8675558556930303753[33] = 0;
   out_8675558556930303753[34] = 0;
   out_8675558556930303753[35] = 0;
   out_8675558556930303753[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8675558556930303753[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8675558556930303753[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8675558556930303753[39] = 0;
   out_8675558556930303753[40] = 0;
   out_8675558556930303753[41] = 0;
   out_8675558556930303753[42] = 0;
   out_8675558556930303753[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8675558556930303753[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8675558556930303753[45] = 0;
   out_8675558556930303753[46] = 0;
   out_8675558556930303753[47] = 0;
   out_8675558556930303753[48] = 0;
   out_8675558556930303753[49] = 0;
   out_8675558556930303753[50] = 0;
   out_8675558556930303753[51] = 0;
   out_8675558556930303753[52] = 0;
   out_8675558556930303753[53] = 0;
   out_8675558556930303753[54] = 0;
   out_8675558556930303753[55] = 0;
   out_8675558556930303753[56] = 0;
   out_8675558556930303753[57] = 1;
   out_8675558556930303753[58] = 0;
   out_8675558556930303753[59] = 0;
   out_8675558556930303753[60] = 0;
   out_8675558556930303753[61] = 0;
   out_8675558556930303753[62] = 0;
   out_8675558556930303753[63] = 0;
   out_8675558556930303753[64] = 0;
   out_8675558556930303753[65] = 0;
   out_8675558556930303753[66] = dt;
   out_8675558556930303753[67] = 0;
   out_8675558556930303753[68] = 0;
   out_8675558556930303753[69] = 0;
   out_8675558556930303753[70] = 0;
   out_8675558556930303753[71] = 0;
   out_8675558556930303753[72] = 0;
   out_8675558556930303753[73] = 0;
   out_8675558556930303753[74] = 0;
   out_8675558556930303753[75] = 0;
   out_8675558556930303753[76] = 1;
   out_8675558556930303753[77] = 0;
   out_8675558556930303753[78] = 0;
   out_8675558556930303753[79] = 0;
   out_8675558556930303753[80] = 0;
   out_8675558556930303753[81] = 0;
   out_8675558556930303753[82] = 0;
   out_8675558556930303753[83] = 0;
   out_8675558556930303753[84] = 0;
   out_8675558556930303753[85] = dt;
   out_8675558556930303753[86] = 0;
   out_8675558556930303753[87] = 0;
   out_8675558556930303753[88] = 0;
   out_8675558556930303753[89] = 0;
   out_8675558556930303753[90] = 0;
   out_8675558556930303753[91] = 0;
   out_8675558556930303753[92] = 0;
   out_8675558556930303753[93] = 0;
   out_8675558556930303753[94] = 0;
   out_8675558556930303753[95] = 1;
   out_8675558556930303753[96] = 0;
   out_8675558556930303753[97] = 0;
   out_8675558556930303753[98] = 0;
   out_8675558556930303753[99] = 0;
   out_8675558556930303753[100] = 0;
   out_8675558556930303753[101] = 0;
   out_8675558556930303753[102] = 0;
   out_8675558556930303753[103] = 0;
   out_8675558556930303753[104] = dt;
   out_8675558556930303753[105] = 0;
   out_8675558556930303753[106] = 0;
   out_8675558556930303753[107] = 0;
   out_8675558556930303753[108] = 0;
   out_8675558556930303753[109] = 0;
   out_8675558556930303753[110] = 0;
   out_8675558556930303753[111] = 0;
   out_8675558556930303753[112] = 0;
   out_8675558556930303753[113] = 0;
   out_8675558556930303753[114] = 1;
   out_8675558556930303753[115] = 0;
   out_8675558556930303753[116] = 0;
   out_8675558556930303753[117] = 0;
   out_8675558556930303753[118] = 0;
   out_8675558556930303753[119] = 0;
   out_8675558556930303753[120] = 0;
   out_8675558556930303753[121] = 0;
   out_8675558556930303753[122] = 0;
   out_8675558556930303753[123] = 0;
   out_8675558556930303753[124] = 0;
   out_8675558556930303753[125] = 0;
   out_8675558556930303753[126] = 0;
   out_8675558556930303753[127] = 0;
   out_8675558556930303753[128] = 0;
   out_8675558556930303753[129] = 0;
   out_8675558556930303753[130] = 0;
   out_8675558556930303753[131] = 0;
   out_8675558556930303753[132] = 0;
   out_8675558556930303753[133] = 1;
   out_8675558556930303753[134] = 0;
   out_8675558556930303753[135] = 0;
   out_8675558556930303753[136] = 0;
   out_8675558556930303753[137] = 0;
   out_8675558556930303753[138] = 0;
   out_8675558556930303753[139] = 0;
   out_8675558556930303753[140] = 0;
   out_8675558556930303753[141] = 0;
   out_8675558556930303753[142] = 0;
   out_8675558556930303753[143] = 0;
   out_8675558556930303753[144] = 0;
   out_8675558556930303753[145] = 0;
   out_8675558556930303753[146] = 0;
   out_8675558556930303753[147] = 0;
   out_8675558556930303753[148] = 0;
   out_8675558556930303753[149] = 0;
   out_8675558556930303753[150] = 0;
   out_8675558556930303753[151] = 0;
   out_8675558556930303753[152] = 1;
   out_8675558556930303753[153] = 0;
   out_8675558556930303753[154] = 0;
   out_8675558556930303753[155] = 0;
   out_8675558556930303753[156] = 0;
   out_8675558556930303753[157] = 0;
   out_8675558556930303753[158] = 0;
   out_8675558556930303753[159] = 0;
   out_8675558556930303753[160] = 0;
   out_8675558556930303753[161] = 0;
   out_8675558556930303753[162] = 0;
   out_8675558556930303753[163] = 0;
   out_8675558556930303753[164] = 0;
   out_8675558556930303753[165] = 0;
   out_8675558556930303753[166] = 0;
   out_8675558556930303753[167] = 0;
   out_8675558556930303753[168] = 0;
   out_8675558556930303753[169] = 0;
   out_8675558556930303753[170] = 0;
   out_8675558556930303753[171] = 1;
   out_8675558556930303753[172] = 0;
   out_8675558556930303753[173] = 0;
   out_8675558556930303753[174] = 0;
   out_8675558556930303753[175] = 0;
   out_8675558556930303753[176] = 0;
   out_8675558556930303753[177] = 0;
   out_8675558556930303753[178] = 0;
   out_8675558556930303753[179] = 0;
   out_8675558556930303753[180] = 0;
   out_8675558556930303753[181] = 0;
   out_8675558556930303753[182] = 0;
   out_8675558556930303753[183] = 0;
   out_8675558556930303753[184] = 0;
   out_8675558556930303753[185] = 0;
   out_8675558556930303753[186] = 0;
   out_8675558556930303753[187] = 0;
   out_8675558556930303753[188] = 0;
   out_8675558556930303753[189] = 0;
   out_8675558556930303753[190] = 1;
   out_8675558556930303753[191] = 0;
   out_8675558556930303753[192] = 0;
   out_8675558556930303753[193] = 0;
   out_8675558556930303753[194] = 0;
   out_8675558556930303753[195] = 0;
   out_8675558556930303753[196] = 0;
   out_8675558556930303753[197] = 0;
   out_8675558556930303753[198] = 0;
   out_8675558556930303753[199] = 0;
   out_8675558556930303753[200] = 0;
   out_8675558556930303753[201] = 0;
   out_8675558556930303753[202] = 0;
   out_8675558556930303753[203] = 0;
   out_8675558556930303753[204] = 0;
   out_8675558556930303753[205] = 0;
   out_8675558556930303753[206] = 0;
   out_8675558556930303753[207] = 0;
   out_8675558556930303753[208] = 0;
   out_8675558556930303753[209] = 1;
   out_8675558556930303753[210] = 0;
   out_8675558556930303753[211] = 0;
   out_8675558556930303753[212] = 0;
   out_8675558556930303753[213] = 0;
   out_8675558556930303753[214] = 0;
   out_8675558556930303753[215] = 0;
   out_8675558556930303753[216] = 0;
   out_8675558556930303753[217] = 0;
   out_8675558556930303753[218] = 0;
   out_8675558556930303753[219] = 0;
   out_8675558556930303753[220] = 0;
   out_8675558556930303753[221] = 0;
   out_8675558556930303753[222] = 0;
   out_8675558556930303753[223] = 0;
   out_8675558556930303753[224] = 0;
   out_8675558556930303753[225] = 0;
   out_8675558556930303753[226] = 0;
   out_8675558556930303753[227] = 0;
   out_8675558556930303753[228] = 1;
   out_8675558556930303753[229] = 0;
   out_8675558556930303753[230] = 0;
   out_8675558556930303753[231] = 0;
   out_8675558556930303753[232] = 0;
   out_8675558556930303753[233] = 0;
   out_8675558556930303753[234] = 0;
   out_8675558556930303753[235] = 0;
   out_8675558556930303753[236] = 0;
   out_8675558556930303753[237] = 0;
   out_8675558556930303753[238] = 0;
   out_8675558556930303753[239] = 0;
   out_8675558556930303753[240] = 0;
   out_8675558556930303753[241] = 0;
   out_8675558556930303753[242] = 0;
   out_8675558556930303753[243] = 0;
   out_8675558556930303753[244] = 0;
   out_8675558556930303753[245] = 0;
   out_8675558556930303753[246] = 0;
   out_8675558556930303753[247] = 1;
   out_8675558556930303753[248] = 0;
   out_8675558556930303753[249] = 0;
   out_8675558556930303753[250] = 0;
   out_8675558556930303753[251] = 0;
   out_8675558556930303753[252] = 0;
   out_8675558556930303753[253] = 0;
   out_8675558556930303753[254] = 0;
   out_8675558556930303753[255] = 0;
   out_8675558556930303753[256] = 0;
   out_8675558556930303753[257] = 0;
   out_8675558556930303753[258] = 0;
   out_8675558556930303753[259] = 0;
   out_8675558556930303753[260] = 0;
   out_8675558556930303753[261] = 0;
   out_8675558556930303753[262] = 0;
   out_8675558556930303753[263] = 0;
   out_8675558556930303753[264] = 0;
   out_8675558556930303753[265] = 0;
   out_8675558556930303753[266] = 1;
   out_8675558556930303753[267] = 0;
   out_8675558556930303753[268] = 0;
   out_8675558556930303753[269] = 0;
   out_8675558556930303753[270] = 0;
   out_8675558556930303753[271] = 0;
   out_8675558556930303753[272] = 0;
   out_8675558556930303753[273] = 0;
   out_8675558556930303753[274] = 0;
   out_8675558556930303753[275] = 0;
   out_8675558556930303753[276] = 0;
   out_8675558556930303753[277] = 0;
   out_8675558556930303753[278] = 0;
   out_8675558556930303753[279] = 0;
   out_8675558556930303753[280] = 0;
   out_8675558556930303753[281] = 0;
   out_8675558556930303753[282] = 0;
   out_8675558556930303753[283] = 0;
   out_8675558556930303753[284] = 0;
   out_8675558556930303753[285] = 1;
   out_8675558556930303753[286] = 0;
   out_8675558556930303753[287] = 0;
   out_8675558556930303753[288] = 0;
   out_8675558556930303753[289] = 0;
   out_8675558556930303753[290] = 0;
   out_8675558556930303753[291] = 0;
   out_8675558556930303753[292] = 0;
   out_8675558556930303753[293] = 0;
   out_8675558556930303753[294] = 0;
   out_8675558556930303753[295] = 0;
   out_8675558556930303753[296] = 0;
   out_8675558556930303753[297] = 0;
   out_8675558556930303753[298] = 0;
   out_8675558556930303753[299] = 0;
   out_8675558556930303753[300] = 0;
   out_8675558556930303753[301] = 0;
   out_8675558556930303753[302] = 0;
   out_8675558556930303753[303] = 0;
   out_8675558556930303753[304] = 1;
   out_8675558556930303753[305] = 0;
   out_8675558556930303753[306] = 0;
   out_8675558556930303753[307] = 0;
   out_8675558556930303753[308] = 0;
   out_8675558556930303753[309] = 0;
   out_8675558556930303753[310] = 0;
   out_8675558556930303753[311] = 0;
   out_8675558556930303753[312] = 0;
   out_8675558556930303753[313] = 0;
   out_8675558556930303753[314] = 0;
   out_8675558556930303753[315] = 0;
   out_8675558556930303753[316] = 0;
   out_8675558556930303753[317] = 0;
   out_8675558556930303753[318] = 0;
   out_8675558556930303753[319] = 0;
   out_8675558556930303753[320] = 0;
   out_8675558556930303753[321] = 0;
   out_8675558556930303753[322] = 0;
   out_8675558556930303753[323] = 1;
}
void h_4(double *state, double *unused, double *out_4851457077302002369) {
   out_4851457077302002369[0] = state[6] + state[9];
   out_4851457077302002369[1] = state[7] + state[10];
   out_4851457077302002369[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_900451339485029709) {
   out_900451339485029709[0] = 0;
   out_900451339485029709[1] = 0;
   out_900451339485029709[2] = 0;
   out_900451339485029709[3] = 0;
   out_900451339485029709[4] = 0;
   out_900451339485029709[5] = 0;
   out_900451339485029709[6] = 1;
   out_900451339485029709[7] = 0;
   out_900451339485029709[8] = 0;
   out_900451339485029709[9] = 1;
   out_900451339485029709[10] = 0;
   out_900451339485029709[11] = 0;
   out_900451339485029709[12] = 0;
   out_900451339485029709[13] = 0;
   out_900451339485029709[14] = 0;
   out_900451339485029709[15] = 0;
   out_900451339485029709[16] = 0;
   out_900451339485029709[17] = 0;
   out_900451339485029709[18] = 0;
   out_900451339485029709[19] = 0;
   out_900451339485029709[20] = 0;
   out_900451339485029709[21] = 0;
   out_900451339485029709[22] = 0;
   out_900451339485029709[23] = 0;
   out_900451339485029709[24] = 0;
   out_900451339485029709[25] = 1;
   out_900451339485029709[26] = 0;
   out_900451339485029709[27] = 0;
   out_900451339485029709[28] = 1;
   out_900451339485029709[29] = 0;
   out_900451339485029709[30] = 0;
   out_900451339485029709[31] = 0;
   out_900451339485029709[32] = 0;
   out_900451339485029709[33] = 0;
   out_900451339485029709[34] = 0;
   out_900451339485029709[35] = 0;
   out_900451339485029709[36] = 0;
   out_900451339485029709[37] = 0;
   out_900451339485029709[38] = 0;
   out_900451339485029709[39] = 0;
   out_900451339485029709[40] = 0;
   out_900451339485029709[41] = 0;
   out_900451339485029709[42] = 0;
   out_900451339485029709[43] = 0;
   out_900451339485029709[44] = 1;
   out_900451339485029709[45] = 0;
   out_900451339485029709[46] = 0;
   out_900451339485029709[47] = 1;
   out_900451339485029709[48] = 0;
   out_900451339485029709[49] = 0;
   out_900451339485029709[50] = 0;
   out_900451339485029709[51] = 0;
   out_900451339485029709[52] = 0;
   out_900451339485029709[53] = 0;
}
void h_10(double *state, double *unused, double *out_9193243756849124789) {
   out_9193243756849124789[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_9193243756849124789[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_9193243756849124789[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2799871591501321246) {
   out_2799871591501321246[0] = 0;
   out_2799871591501321246[1] = 9.8100000000000005*cos(state[1]);
   out_2799871591501321246[2] = 0;
   out_2799871591501321246[3] = 0;
   out_2799871591501321246[4] = -state[8];
   out_2799871591501321246[5] = state[7];
   out_2799871591501321246[6] = 0;
   out_2799871591501321246[7] = state[5];
   out_2799871591501321246[8] = -state[4];
   out_2799871591501321246[9] = 0;
   out_2799871591501321246[10] = 0;
   out_2799871591501321246[11] = 0;
   out_2799871591501321246[12] = 1;
   out_2799871591501321246[13] = 0;
   out_2799871591501321246[14] = 0;
   out_2799871591501321246[15] = 1;
   out_2799871591501321246[16] = 0;
   out_2799871591501321246[17] = 0;
   out_2799871591501321246[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2799871591501321246[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2799871591501321246[20] = 0;
   out_2799871591501321246[21] = state[8];
   out_2799871591501321246[22] = 0;
   out_2799871591501321246[23] = -state[6];
   out_2799871591501321246[24] = -state[5];
   out_2799871591501321246[25] = 0;
   out_2799871591501321246[26] = state[3];
   out_2799871591501321246[27] = 0;
   out_2799871591501321246[28] = 0;
   out_2799871591501321246[29] = 0;
   out_2799871591501321246[30] = 0;
   out_2799871591501321246[31] = 1;
   out_2799871591501321246[32] = 0;
   out_2799871591501321246[33] = 0;
   out_2799871591501321246[34] = 1;
   out_2799871591501321246[35] = 0;
   out_2799871591501321246[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2799871591501321246[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2799871591501321246[38] = 0;
   out_2799871591501321246[39] = -state[7];
   out_2799871591501321246[40] = state[6];
   out_2799871591501321246[41] = 0;
   out_2799871591501321246[42] = state[4];
   out_2799871591501321246[43] = -state[3];
   out_2799871591501321246[44] = 0;
   out_2799871591501321246[45] = 0;
   out_2799871591501321246[46] = 0;
   out_2799871591501321246[47] = 0;
   out_2799871591501321246[48] = 0;
   out_2799871591501321246[49] = 0;
   out_2799871591501321246[50] = 1;
   out_2799871591501321246[51] = 0;
   out_2799871591501321246[52] = 0;
   out_2799871591501321246[53] = 1;
}
void h_13(double *state, double *unused, double *out_6658774396801807001) {
   out_6658774396801807001[0] = state[3];
   out_6658774396801807001[1] = state[4];
   out_6658774396801807001[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4734206802787553733) {
   out_4734206802787553733[0] = 0;
   out_4734206802787553733[1] = 0;
   out_4734206802787553733[2] = 0;
   out_4734206802787553733[3] = 1;
   out_4734206802787553733[4] = 0;
   out_4734206802787553733[5] = 0;
   out_4734206802787553733[6] = 0;
   out_4734206802787553733[7] = 0;
   out_4734206802787553733[8] = 0;
   out_4734206802787553733[9] = 0;
   out_4734206802787553733[10] = 0;
   out_4734206802787553733[11] = 0;
   out_4734206802787553733[12] = 0;
   out_4734206802787553733[13] = 0;
   out_4734206802787553733[14] = 0;
   out_4734206802787553733[15] = 0;
   out_4734206802787553733[16] = 0;
   out_4734206802787553733[17] = 0;
   out_4734206802787553733[18] = 0;
   out_4734206802787553733[19] = 0;
   out_4734206802787553733[20] = 0;
   out_4734206802787553733[21] = 0;
   out_4734206802787553733[22] = 1;
   out_4734206802787553733[23] = 0;
   out_4734206802787553733[24] = 0;
   out_4734206802787553733[25] = 0;
   out_4734206802787553733[26] = 0;
   out_4734206802787553733[27] = 0;
   out_4734206802787553733[28] = 0;
   out_4734206802787553733[29] = 0;
   out_4734206802787553733[30] = 0;
   out_4734206802787553733[31] = 0;
   out_4734206802787553733[32] = 0;
   out_4734206802787553733[33] = 0;
   out_4734206802787553733[34] = 0;
   out_4734206802787553733[35] = 0;
   out_4734206802787553733[36] = 0;
   out_4734206802787553733[37] = 0;
   out_4734206802787553733[38] = 0;
   out_4734206802787553733[39] = 0;
   out_4734206802787553733[40] = 0;
   out_4734206802787553733[41] = 1;
   out_4734206802787553733[42] = 0;
   out_4734206802787553733[43] = 0;
   out_4734206802787553733[44] = 0;
   out_4734206802787553733[45] = 0;
   out_4734206802787553733[46] = 0;
   out_4734206802787553733[47] = 0;
   out_4734206802787553733[48] = 0;
   out_4734206802787553733[49] = 0;
   out_4734206802787553733[50] = 0;
   out_4734206802787553733[51] = 0;
   out_4734206802787553733[52] = 0;
   out_4734206802787553733[53] = 0;
}
void h_14(double *state, double *unused, double *out_3195839728228906936) {
   out_3195839728228906936[0] = state[6];
   out_3195839728228906936[1] = state[7];
   out_3195839728228906936[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3983239771780402005) {
   out_3983239771780402005[0] = 0;
   out_3983239771780402005[1] = 0;
   out_3983239771780402005[2] = 0;
   out_3983239771780402005[3] = 0;
   out_3983239771780402005[4] = 0;
   out_3983239771780402005[5] = 0;
   out_3983239771780402005[6] = 1;
   out_3983239771780402005[7] = 0;
   out_3983239771780402005[8] = 0;
   out_3983239771780402005[9] = 0;
   out_3983239771780402005[10] = 0;
   out_3983239771780402005[11] = 0;
   out_3983239771780402005[12] = 0;
   out_3983239771780402005[13] = 0;
   out_3983239771780402005[14] = 0;
   out_3983239771780402005[15] = 0;
   out_3983239771780402005[16] = 0;
   out_3983239771780402005[17] = 0;
   out_3983239771780402005[18] = 0;
   out_3983239771780402005[19] = 0;
   out_3983239771780402005[20] = 0;
   out_3983239771780402005[21] = 0;
   out_3983239771780402005[22] = 0;
   out_3983239771780402005[23] = 0;
   out_3983239771780402005[24] = 0;
   out_3983239771780402005[25] = 1;
   out_3983239771780402005[26] = 0;
   out_3983239771780402005[27] = 0;
   out_3983239771780402005[28] = 0;
   out_3983239771780402005[29] = 0;
   out_3983239771780402005[30] = 0;
   out_3983239771780402005[31] = 0;
   out_3983239771780402005[32] = 0;
   out_3983239771780402005[33] = 0;
   out_3983239771780402005[34] = 0;
   out_3983239771780402005[35] = 0;
   out_3983239771780402005[36] = 0;
   out_3983239771780402005[37] = 0;
   out_3983239771780402005[38] = 0;
   out_3983239771780402005[39] = 0;
   out_3983239771780402005[40] = 0;
   out_3983239771780402005[41] = 0;
   out_3983239771780402005[42] = 0;
   out_3983239771780402005[43] = 0;
   out_3983239771780402005[44] = 1;
   out_3983239771780402005[45] = 0;
   out_3983239771780402005[46] = 0;
   out_3983239771780402005[47] = 0;
   out_3983239771780402005[48] = 0;
   out_3983239771780402005[49] = 0;
   out_3983239771780402005[50] = 0;
   out_3983239771780402005[51] = 0;
   out_3983239771780402005[52] = 0;
   out_3983239771780402005[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4299274199831556809) {
  err_fun(nom_x, delta_x, out_4299274199831556809);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2345037795202932384) {
  inv_err_fun(nom_x, true_x, out_2345037795202932384);
}
void pose_H_mod_fun(double *state, double *out_2098398821367927813) {
  H_mod_fun(state, out_2098398821367927813);
}
void pose_f_fun(double *state, double dt, double *out_5430492952832692036) {
  f_fun(state,  dt, out_5430492952832692036);
}
void pose_F_fun(double *state, double dt, double *out_8675558556930303753) {
  F_fun(state,  dt, out_8675558556930303753);
}
void pose_h_4(double *state, double *unused, double *out_4851457077302002369) {
  h_4(state, unused, out_4851457077302002369);
}
void pose_H_4(double *state, double *unused, double *out_900451339485029709) {
  H_4(state, unused, out_900451339485029709);
}
void pose_h_10(double *state, double *unused, double *out_9193243756849124789) {
  h_10(state, unused, out_9193243756849124789);
}
void pose_H_10(double *state, double *unused, double *out_2799871591501321246) {
  H_10(state, unused, out_2799871591501321246);
}
void pose_h_13(double *state, double *unused, double *out_6658774396801807001) {
  h_13(state, unused, out_6658774396801807001);
}
void pose_H_13(double *state, double *unused, double *out_4734206802787553733) {
  H_13(state, unused, out_4734206802787553733);
}
void pose_h_14(double *state, double *unused, double *out_3195839728228906936) {
  h_14(state, unused, out_3195839728228906936);
}
void pose_H_14(double *state, double *unused, double *out_3983239771780402005) {
  H_14(state, unused, out_3983239771780402005);
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
